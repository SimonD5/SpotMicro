import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

# Ajout des dossiers du projet au chemin d'import pour supporter les deux modes d'import
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PI_DIR = os.path.join(REPO_ROOT, "robot", "pi")
PC_DIR = os.path.join(REPO_ROOT, "pc")
for _path in (REPO_ROOT, PI_DIR, PC_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import config as pc_config
import text_client
import voice_client
import emotions
import emotions_data
import emotion_server
import predict_emotion
import train_emotion_model


class FakeEmbedder:
    """Simule SentenceTransformer sans charger de modèle réel."""

    def __init__(self):
        self.encoded_inputs = []

    def encode(self, texts, show_progress_bar=False):
        self.encoded_inputs.append(list(texts))
        return [[float(len(t)), 1.0] for t in texts]


class FakeClassifier:
    """Simule le classifieur scikit-learn LogisticRegression."""

    def __init__(self, predicted_emotion="content", probas=None):
        self.predicted_emotion = predicted_emotion
        self.probas = probas or [0.886, 0.05, 0.02, 0.01, 0.01, 0.01, 0.014]
        self.fitted = False

    def fit(self, x_vec, y_labels):
        self.fitted = True
        return self

    def predict(self, x_vec):
        if callable(self.predicted_emotion):
            return [self.predicted_emotion(i, v) for i, v in enumerate(x_vec)]
        return [self.predicted_emotion for _ in x_vec]

    def predict_proba(self, x_vec):
        return [list(self.probas) for _ in x_vec]


class FakeSocket:
    """Socket TCP simulé permettant de tester fragmentation, coalescence et pannes réseau."""

    def __init__(self, recv_chunks=None, connect_error=None, send_error=None):
        self.recv_chunks = list(recv_chunks or [])
        self.connect_error = connect_error
        self.send_error = send_error
        self.sent_payloads = []
        self.connected_to = None
        self.closed = False
        self.bound_to = None
        self.listening = False

    def setsockopt(self, *args, **kwargs):
        pass

    def bind(self, addr):
        self.bound_to = addr

    def listen(self, backlog):
        self.listening = True

    def connect(self, addr):
        if self.connect_error is not None:
            raise self.connect_error
        self.connected_to = addr

    def recv(self, bufsize):
        if not self.recv_chunks:
            return b""
        item = self.recv_chunks.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def sendall(self, data):
        if self.send_error is not None:
            raise self.send_error
        self.sent_payloads.append(bytes(data))

    def close(self):
        self.closed = True


class TestImportsAndData(unittest.TestCase):
    """Vérifie que les modules s'importent sans GPIO ni modèles et que les données sont cohérentes."""

    def test_emotions_data_structure(self):
        expected = [
            "content",
            "triste",
            "curieux",
            "surpris",
            "colere",
            "peur",
            "neutre",
        ]
        self.assertEqual(emotions_data.EMOTIONS, expected)
        for emo in expected:
            self.assertIn(emo, emotions_data.TRAIN)
            self.assertIn(emo, emotions_data.TEST)
            self.assertGreaterEqual(len(emotions_data.TRAIN[emo]), 20)
            self.assertGreaterEqual(len(emotions_data.TEST[emo]), 5)
            train_set = set(emotions_data.TRAIN[emo])
            test_set = set(emotions_data.TEST[emo])
            self.assertTrue(train_set.isdisjoint(test_set))


class TestPathsAndModelConsistency(unittest.TestCase):
    """Vérifie la résolution des chemins et la cohérence du modèle multilingue."""

    def test_default_model_is_multilingual_minilm(self):
        expected_model = "paraphrase-multilingual-MiniLM-L12-v2"
        self.assertEqual(emotion_server.DEFAULT_MODEL_NAME, expected_model)
        self.assertEqual(predict_emotion.DEFAULT_MODEL_NAME, expected_model)
        self.assertEqual(train_emotion_model.DEFAULT_MODEL_NAME, expected_model)

    def test_resolve_model_and_classifier_paths_hierarchy(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmpdir:
            root_dir = tmpdir
            base_dir = os.path.join(root_dir, "robot")
            script_dir = os.path.join(base_dir, "pi")
            os.makedirs(script_dir, exist_ok=True)

            # 1. Aucun dossier local -> fallback multilingue et chemin script_dir pour le classifieur
            self.assertEqual(
                emotion_server.resolve_model_path(script_dir),
                "paraphrase-multilingual-MiniLM-L12-v2",
            )
            self.assertEqual(
                emotion_server.resolve_classifier_path(script_dir),
                os.path.join(script_dir, "emotion_classifier.joblib"),
            )

            # 2. Présence à la racine (root_dir)
            root_model = os.path.join(root_dir, "model_minilm")
            os.makedirs(root_model, exist_ok=True)
            root_clf = os.path.join(root_dir, "emotion_classifier.joblib")
            with open(root_clf, "wb") as f:
                f.write(b"dummy")

            self.assertEqual(emotion_server.resolve_model_path(script_dir), root_model)
            self.assertEqual(
                emotion_server.resolve_classifier_path(script_dir), root_clf
            )

            # 3. Priorité au dossier pi/ (script_dir)
            pi_model = os.path.join(script_dir, "model_minilm")
            os.makedirs(pi_model, exist_ok=True)
            pi_clf = os.path.join(script_dir, "emotion_classifier.joblib")
            with open(pi_clf, "wb") as f:
                f.write(b"dummy_pi")

            self.assertEqual(emotion_server.resolve_model_path(script_dir), pi_model)
            self.assertEqual(
                emotion_server.resolve_classifier_path(script_dir), pi_clf
            )
            self.assertEqual(predict_emotion.resolve_model_path(script_dir), pi_model)
            self.assertEqual(
                predict_emotion.resolve_classifier_path(script_dir), pi_clf
            )
            self.assertEqual(
                train_emotion_model.resolve_model_path(script_dir), pi_model
            )

    def test_train_output_classifier_is_anchored_to_script_dir(self):
        self.assertEqual(
            train_emotion_model.OUTPUT_CLASSIFIER,
            os.path.join(train_emotion_model.SCRIPT_DIR, "emotion_classifier.joblib"),
        )


class TestEmotionServerTCP(unittest.TestCase):
    """Vérifie le contrat TCP du serveur : fragmentation, UTF-8 coupé, coalescence, déconnexions."""

    def test_fragmented_utf8_request_across_chunks(self):
        phrase = "J'ai réussi mon été à l'école !"
        encoded = (phrase + "\n").encode("utf-8")
        # Découpage volontaire au milieu d'un caractère UTF-8 multi-octets (0xC3 0xA9)
        split_idx = encoded.index(b"\xc3\xa9") + 1
        chunks = [encoded[:split_idx], encoded[split_idx:], b""]

        sock = FakeSocket(recv_chunks=chunks)
        embedder = FakeEmbedder()
        classifier = FakeClassifier(predicted_emotion="content")
        played = []

        with mock.patch("sys.stdout", new_callable=io.StringIO):
            emotion_server.handle_client(
                sock,
                ("127.0.0.1", 50000),
                embedder,
                classifier,
                buzzer_fn=played.append,
            )

        self.assertTrue(sock.closed)
        self.assertEqual(played, ["content"])
        self.assertEqual(len(sock.sent_payloads), 1)
        raw_reply = sock.sent_payloads[0]
        self.assertTrue(raw_reply.endswith(b"\n"))
        reply = json.loads(raw_reply.decode("utf-8"))
        self.assertEqual(set(reply.keys()), {"texte", "emotion", "confiance", "ms"})
        self.assertEqual(reply["texte"], phrase)
        self.assertEqual(reply["emotion"], "content")

    def test_coalesced_multiple_lines_in_single_recv(self):
        coalesced = "Première phrase\n\nDeuxième phrase\r\nTroisième phrase\n".encode(
            "utf-8"
        )
        sock = FakeSocket(recv_chunks=[coalesced, b""])
        embedder = FakeEmbedder()
        emotions_seq = ["content", "triste", "curieux"]
        call_idx = {"i": 0}

        def pred_fn(_idx, _vec):
            val = emotions_seq[call_idx["i"]]
            call_idx["i"] += 1
            return val

        classifier = FakeClassifier(predicted_emotion=pred_fn)
        played = []

        with mock.patch("sys.stdout", new_callable=io.StringIO):
            emotion_server.handle_client(
                sock,
                ("127.0.0.1", 50001),
                embedder,
                classifier,
                buzzer_fn=played.append,
            )

        self.assertTrue(sock.closed)
        self.assertEqual(played, ["content", "triste", "curieux"])
        self.assertEqual(len(sock.sent_payloads), 3)
        decoded_replies = [
            json.loads(p.decode("utf-8")) for p in sock.sent_payloads
        ]
        self.assertEqual(
            [r["texte"] for r in decoded_replies],
            ["Première phrase", "Deuxième phrase", "Troisième phrase"],
        )
        self.assertEqual(
            [r["emotion"] for r in decoded_replies],
            ["content", "triste", "curieux"],
        )

    def test_resilience_to_abrupt_client_disconnect_and_socket_closing(self):
        # Client 1 provoque ConnectionResetError, Client 2 envoie une requête normale
        client1 = FakeSocket(recv_chunks=[ConnectionResetError("Connexion réinitialisée")])
        client2 = FakeSocket(recv_chunks=["Bonjour\n".encode("utf-8"), b""])
        server_sock = FakeSocket()
        accepted = [(client1, ("192.168.1.10", 51001)), (client2, ("192.168.1.10", 51002))]
        server_sock.accept = mock.MagicMock(side_effect=accepted)

        embedder = FakeEmbedder()
        classifier = FakeClassifier(predicted_emotion="neutre")
        played = []

        with (
            mock.patch("emotion_server.socket.socket", return_value=server_sock),
            mock.patch("sys.stdout", new_callable=io.StringIO),
        ):
            emotion_server.run_server(
                embedder=embedder,
                classifier=classifier,
                buzzer_fn=played.append,
                max_clients=2,
            )

        self.assertTrue(client1.closed)
        self.assertTrue(client2.closed)
        self.assertTrue(server_sock.closed)
        self.assertEqual(played, ["neutre"])
        self.assertEqual(len(client2.sent_payloads), 1)


class TestPCClients(unittest.TestCase):
    """Vérifie la configuration IP, le protocole par lignes et la fermeture socket côté PC."""

    def test_config_and_voice_client_ip_alignment(self):
        self.assertEqual(pc_config.PI_IP, "192.168.1.28")
        self.assertEqual(pc_config.PORT, 5005)
        self.assertEqual(voice_client.PI_IP, pc_config.PI_IP)
        self.assertEqual(voice_client.PORT, pc_config.PORT)

    def test_send_emotion_request_fragmented_utf8_response_and_coalescence(self):
        resp1 = {
            "texte": "Café chaud",
            "emotion": "content",
            "confiance": 91.2,
            "ms": 14.5,
        }
        resp2 = {
            "texte": "Été",
            "emotion": "neutre",
            "confiance": 80.0,
            "ms": 12.1,
        }
        raw1 = (json.dumps(resp1, ensure_ascii=False) + "\n").encode("utf-8")
        raw2 = (json.dumps(resp2, ensure_ascii=False) + "\n").encode("utf-8")
        # Fragmentation au milieu du caractère UTF-8 'é' + coalescence avec le début de raw2
        split_pos = raw1.index(b"\xc3\xa9") + 1
        chunks = [raw1[:split_pos], raw1[split_pos:] + raw2[:5], raw2[5:]]

        sock = FakeSocket(recv_chunks=chunks)
        parsed1, buf = text_client.send_emotion_request(sock, "Café\nchaud")
        parsed2, buf = text_client.send_emotion_request(sock, "Été", buffer=buf)

        self.assertEqual(
            sock.sent_payloads,
            ["Café chaud\n".encode("utf-8"), "Été\n".encode("utf-8")],
        )
        self.assertEqual(parsed1, resp1)
        self.assertEqual(parsed2, resp2)
        self.assertEqual(buf, b"")

    def test_voice_client_sends_newline_and_closes_socket_on_error(self):
        # 1. Échec de connexion : le socket doit quand même être fermé
        failing_sock = FakeSocket(connect_error=ConnectionRefusedError("Refusé"))
        with mock.patch("sys.stdout", new_callable=io.StringIO):
            rc = voice_client.main(
                recognizer=mock.MagicMock(),
                mic_factory=mock.MagicMock(),
                socket_factory=lambda *a, **kw: failing_sock,
            )
        self.assertEqual(rc, 1)
        self.assertTrue(failing_sock.closed)

        # 2. Envoi d'une phrase transcrite puis déconnexion serveur
        resp = {
            "texte": "Bonjour robot",
            "emotion": "content",
            "confiance": 95.0,
            "ms": 15.0,
        }
        active_sock = FakeSocket(
            recv_chunks=[(json.dumps(resp) + "\n").encode("utf-8"), b""]
        )
        fake_recognizer = mock.MagicMock()
        fake_recognizer.listen.side_effect = ["audio1", "audio2"]
        fake_recognizer.recognize_google.side_effect = [
            "Bonjour robot",
            "Deuxième phrase",
        ]
        fake_mic = mock.MagicMock()

        with mock.patch("sys.stdout", new_callable=io.StringIO):
            rc = voice_client.main(
                recognizer=fake_recognizer,
                mic_factory=lambda: fake_mic,
                socket_factory=lambda *a, **kw: active_sock,
            )
        self.assertEqual(rc, 0)
        self.assertTrue(active_sock.closed)
        self.assertEqual(
            active_sock.sent_payloads[0], "Bonjour robot\n".encode("utf-8")
        )


class TestTrainAndPredict(unittest.TestCase):
    """Vérifie l'entraînement et le testeur interactif avec dépendances simulées."""

    def test_train_and_evaluate_with_mocks(self):
        embedder = FakeEmbedder()
        classifier = FakeClassifier(predicted_emotion="content")
        saved = {}

        def fake_dump(obj, path):
            saved["obj"] = obj
            saved["path"] = path

        with mock.patch("sys.stdout", new_callable=io.StringIO):
            clf, acc, inf_time = train_emotion_model.train_and_evaluate(
                model_path="paraphrase-multilingual-MiniLM-L12-v2",
                output_classifier="test_out.joblib",
                embedder=embedder,
                classifier=classifier,
                dump_fn=fake_dump,
            )

        self.assertIs(clf, classifier)
        self.assertTrue(classifier.fitted)
        self.assertEqual(saved["path"], "test_out.joblib")
        self.assertGreater(acc, 0.0)
        self.assertGreaterEqual(inf_time, 0.0)

    def test_predict_emotion_interactive_loop(self):
        embedder = FakeEmbedder()
        classifier = FakeClassifier(predicted_emotion="surpris")
        inputs = iter(["Waouh quelle surprise !", "quitter"])

        with mock.patch("sys.stdout", new_callable=io.StringIO) as fake_out:
            predict_emotion.main(
                embedder=embedder,
                classifier=classifier,
                input_fn=lambda _prompt: next(inputs),
            )

        self.assertIn("[SURPRIS]", fake_out.getvalue())


if __name__ == "__main__":
    unittest.main()
