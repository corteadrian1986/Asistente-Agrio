import ast
import base64
import datetime
import json
import math
import operator
import os
import random
import re
import ssl
import struct
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import wave

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.metrics import dp
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

DATA_FILE = "agrio_data.json"
ERROR_LOG_FILE = "agrio_errors.log"
ENV_FILE = ".env"
POMODORO_SECONDS = 25 * 60
PC_WAKE_SCAN_SECONDS = 4.5
# Pydroid 3 no declara el permiso de micrófono (no aparece en Ajustes > Apps > Permisos),
# así que en Android se dicta con el micrófono del teclado. Pon False solo si compilas
# tu propio APK con RECORD_AUDIO (buildozer).
ANDROID_USE_KEYBOARD_DICTATION = False
KEYBOARD_VOICE_IDLE_SECONDS = 3.0
# Mantiene la pantalla encendida mientras Agrio está abierto (hasta que bloquees el celular).
KEEP_SCREEN_ON = True
PC_ACTIVE_LISTEN_SECONDS = 8.0

# IMPORTANTE: pon el token y el chat id de Telegram en el menú de Agrio o en el archivo .env
# (XIAOZHI_TELEGRAM_BOT_TOKEN=... y XIAOZHI_TELEGRAM_CHAT_ID=...).
DEFAULT_TELEGRAM_TOKEN = ""
DEFAULT_TELEGRAM_CHAT_ID = ""
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
TRANSCRIBE_FALLBACK_MODEL = "gemini-2.5-flash"

GEMINI_MODEL_OPTIONS = (
    "gemini-2.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
)

ACCENT_PRESETS = {
    "Lima": [0.71, 1.0, 0.26, 1.0],
    "Morado": [0.66, 0.30, 1.0, 1.0],
    "Cian": [0.30, 0.79, 1.0, 1.0],
    "Rosa": [1.0, 0.44, 0.69, 1.0],
    "Ámbar": [1.0, 0.71, 0.28, 1.0],
    "Rojo Neón": [1.0, 0.18, 0.28, 1.0],
    "Verde Esmeralda": [0.12, 0.92, 0.56, 1.0],
    "Azul Eléctrico": [0.22, 0.52, 1.0, 1.0],
    "Naranja Fuego": [1.0, 0.42, 0.12, 1.0],
    "Magenta": [0.95, 0.20, 0.82, 1.0],
    "Coral": [1.0, 0.48, 0.42, 1.0],
    "Menta": [0.45, 1.0, 0.78, 1.0],
    "Violeta": [0.52, 0.25, 0.95, 1.0],
    "Blanco Puro": [0.96, 0.98, 1.0, 1.0],
}

DIAS_ES = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]

MESES_ES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]

GREETINGS = [
    "¡Qué onda! Aquí anda Agrio, dime qué necesitas.",
    "¡Hola! Ya te escucho, ¿en qué te ayudo?",
    "¡Buenas! ¿Qué vamos a hacer hoy?",
]

HOW_ARE_YOU = [
    "Aquí firmes, con la batería puesta y sin quejarme mucho.",
    "Todo en orden por acá. ¿Tú cómo vas?",
    "Listo para trabajar o platicar, tú manda.",
]

JOKES = [
    "¿Por qué la computadora tenía frío? Porque dejó abierta la ventana.",
    "Un bloque de 25 minutos sin distracciones hace maravillas; te lo dice Agrio.",
    "Si apagas el ruido y te enfocas, avanzas el doble.",
]

MOTIVATION = [
    "Dale con todo, un paso a la vez también es avance.",
    "Menos vueltas y más acción; tú puedes con esto.",
    "Mantén el enfoque, que el trabajo constante siempre rinde.",
]

TOUCH_PHRASES = [
    ("¡Gracias!", "happy"),
    ("¡Hey, despacio!", "surprised"),
    ("¡No molestes!", "annoyed"),
    ("¿Qué pasa?", "speaking"),
    ("¡Cuidado con la cara!", "surprised"),
    ("¡Aquí ando, dime!", "happy"),
    ("¡Aguas, que me haces cosquillas!", "surprised"),
    ("¡Ey, aguas con el dedo!", "annoyed"),
]


def _rgba(col):
    try:
        if not col or len(col) < 4:
            return (0.71, 1.0, 0.26, 1.0)
        return (float(col[0]), float(col[1]), float(col[2]), float(col[3]))
    except Exception:
        return (0.71, 1.0, 0.26, 1.0)


def log_error(context_tag, exc_or_msg):
    try:
        if os.path.exists(ERROR_LOG_FILE) and os.path.getsize(ERROR_LOG_FILE) > 1_500_000:
            backup = ERROR_LOG_FILE + ".old"
            if os.path.exists(backup):
                os.remove(backup)
            os.replace(ERROR_LOG_FILE, backup)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(exc_or_msg, BaseException):
            tb = "".join(
                traceback.format_exception(
                    type(exc_or_msg), exc_or_msg, exc_or_msg.__traceback__
                )
            )
            detail = tb.strip()
        else:
            detail = str(exc_or_msg)
        line = f"[{ts}] [{context_tag}] {detail}\n{'-' * 50}\n"
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
        print(f"[{context_tag}] {str(exc_or_msg)[:140]}", flush=True)
    except Exception:
        pass


def read_last_error_summary():
    try:
        if not os.path.exists(ERROR_LOG_FILE):
            return "Sin errores registrados en agrio_errors.log"
        with open(ERROR_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()
        if not content:
            return "Log vacío (sin errores)"
        blocks = [b.strip() for b in content.split("-" * 50) if b.strip()]
        return blocks[-1][-240:] if blocks else "Sin detalle"
    except Exception as exc:
        return f"No pude leer log: {exc}"


def _build_ssl_context(allow_unverified=False):
    if allow_unverified:
        return ssl._create_unverified_context()
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _urlopen_with_ssl_fallback(req, timeout=12):
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=_build_ssl_context(False))
    except urllib.error.URLError as uerr:
        if "CERTIFICATE_VERIFY_FAILED" in str(uerr):
            return urllib.request.urlopen(req, timeout=timeout, context=_build_ssl_context(True))
        raise


def _cleanup_old_temp_audio(max_age_sec=120):
    removed = 0
    try:
        tmp_dir = tempfile.gettempdir()
        now = time.time()
        for fname in os.listdir(tmp_dir):
            if not (
                fname.startswith("agrio_tts_")
                or fname.startswith("agrio_mic_")
                or fname.startswith("agrio_vox_")
            ):
                continue
            fpath = os.path.join(tmp_dir, fname)
            try:
                if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > max_age_sec:
                    os.remove(fpath)
                    removed += 1
            except Exception:
                pass
    except Exception:
        pass
    return removed


def load_env_file(filepath=ENV_FILE):
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception as exc:
        log_error("ENV", exc)


def _gemini_generate(api_key, model, parts, max_tokens=140, temperature=0.7, timeout=20):
    """Llamada simple a Gemini generateContent. Devuelve el texto o lanza excepción."""
    model = str(model or DEFAULT_GEMINI_MODEL).strip()
    if model.startswith("models/"):
        model = model.split("/", 1)[1]
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={urllib.parse.quote(api_key)}"
    )
    payload = json.dumps(
        {
            "contents": [{"parts": parts}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with _urlopen_with_ssl_fallback(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    out = ""
    for cand in data.get("candidates") or []:
        for pt in (cand.get("content") or {}).get("parts") or []:
            if isinstance(pt, dict) and pt.get("text"):
                out += str(pt["text"])
    return out.strip()


_KEEP_ON_STATE = {"wakelock": None, "runner": None}


def set_keep_screen_on(enable=True):
    """Mantiene la pantalla encendida en Android. Prueba tres métodos y devuelve cuáles funcionaron."""
    worked = []
    try:
        Window.allow_screensaver = not enable
        worked.append("kivy")
    except Exception as exc:
        log_error("KEEP_ON_KIVY", exc)

    try:
        from jnius import autoclass, PythonJavaClass, java_method  # type: ignore
    except Exception:
        return ",".join(worked)

    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        if activity is None:
            return ",".join(worked)
    except Exception as exc:
        log_error("KEEP_ON_ACTIVITY", exc)
        return ",".join(worked)

    try:
        LayoutParams = autoclass("android.view.WindowManager$LayoutParams")
        flag = LayoutParams.FLAG_KEEP_SCREEN_ON

        class _Runner(PythonJavaClass):
            __javainterfaces__ = ["java/lang/Runnable"]
            __javacontext__ = "app"

            def __init__(self, fn):
                super().__init__()
                self.fn = fn

            @java_method("()V")
            def run(self):
                try:
                    self.fn()
                except Exception as e:
                    log_error("KEEP_ON_RUN", e)

        def _apply():
            w = activity.getWindow()
            if enable:
                w.addFlags(flag)
            else:
                w.clearFlags(flag)

        runner = _Runner(_apply)
        _KEEP_ON_STATE["runner"] = runner
        activity.runOnUiThread(runner)
        worked.append("window")
    except Exception as exc:
        log_error("KEEP_ON_WINDOW", exc)

    try:
        Context = autoclass("android.content.Context")
        PowerManager = autoclass("android.os.PowerManager")
        pm = activity.getSystemService(Context.POWER_SERVICE)
        if enable:
            if _KEEP_ON_STATE["wakelock"] is None:
                wl = pm.newWakeLock(
                    PowerManager.SCREEN_BRIGHT_WAKE_LOCK | PowerManager.ON_AFTER_RELEASE,
                    "Agrio:screen",
                )
                wl.setReferenceCounted(False)
                wl.acquire()
                _KEEP_ON_STATE["wakelock"] = wl
            worked.append("wakelock")
        elif _KEEP_ON_STATE["wakelock"] is not None:
            _KEEP_ON_STATE["wakelock"].release()
            _KEEP_ON_STATE["wakelock"] = None
    except Exception as exc:
        log_error("KEEP_ON_WAKELOCK", exc)

    print(
        f"[PANTALLA] mantener encendida={enable}; métodos: {','.join(worked) or 'ninguno'}",
        flush=True,
    )
    return ",".join(worked)


class AgrioListener:
    """Escucha voz.

    Android (Pydroid 3): graba con AudioRecord (sin callbacks ni Proxy de jnius),
    guarda un WAV y lo transcribe con Gemini.
    PC: sounddevice + SpeechRecognition.
    """

    def __init__(
        self,
        on_result=None,
        on_error=None,
        on_done=None,
        on_phase=None,
        get_api_key=None,
        get_model=None,
    ):
        self.on_result = on_result
        self.on_error = on_error
        self.on_done = on_done
        self.on_phase = on_phase
        self.get_api_key = get_api_key
        self.get_model = get_model
        self.available = False
        self.mode = "none"
        self.is_listening = False
        self.is_background_scan = False
        self._waiting_result = False
        self._watchdog_ev = None
        self._sd = None
        self._wav_write = None
        self._sr = None
        self._init_backends()

    def _init_backends(self):
        try:
            from jnius import autoclass  # type: ignore

            autoclass("android.media.AudioRecord")
            self.available = True
            self.mode = "android"
            return
        except Exception as exc:
            log_error("MIC_INIT_ANDROID", exc)

        try:
            import sounddevice as sd  # type: ignore
            from scipy.io.wavfile import write as wav_write  # type: ignore
            import speech_recognition as sr  # type: ignore

            self._sd = sd
            self._wav_write = wav_write
            self._sr = sr
            self.available = True
            self.mode = "pc_mic"
        except Exception:
            self.available = False
            self.mode = "none"

    def _clear_waiting(self):
        self._waiting_result = False
        self.is_listening = False
        if self._watchdog_ev:
            try:
                self._watchdog_ev.cancel()
            except Exception:
                pass
            self._watchdog_ev = None

    def _finish_cycle(self):
        was_bg = self.is_background_scan
        self.is_background_scan = False
        self._clear_waiting()
        if callable(self.on_done):
            Clock.schedule_once(lambda *_, bg=was_bg: self.on_done(bg), 0)

    def _emit_phase(self, text):
        if callable(self.on_phase):
            Clock.schedule_once(lambda *_, t=text: self.on_phase(t), 0)

    def _transcribe_with_gemini(self, wav_path):
        key = "".join(
            str(self.get_api_key() if callable(self.get_api_key) else "").split()
        )
        if not key:
            raise RuntimeError("Falta Gemini API Key (configúrala en el Menú)")
        with open(wav_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")

        parts = [
            {
                "text": (
                    "Transcribe literalmente este audio en español. "
                    "Responde solo con la transcripción, sin comillas ni comentarios. "
                    "Si no hay voz clara, responde exactamente: [SIN_VOZ]"
                )
            },
            {"inline_data": {"mime_type": "audio/wav", "data": b64}},
        ]

        models = []
        primary = str(self.get_model() if callable(self.get_model) else "").strip()
        if primary:
            models.append(primary)
        if TRANSCRIBE_FALLBACK_MODEL not in models:
            models.append(TRANSCRIBE_FALLBACK_MODEL)

        last_exc = None
        for m in models:
            for attempt in range(2):
                try:
                    out = _gemini_generate(
                        key, m, parts, max_tokens=200, temperature=0.0, timeout=25
                    )
                    if not out or "[SIN_VOZ]" in out:
                        return ""
                    return out.strip()
                except urllib.error.HTTPError as he:
                    last_exc = he
                    body = ""
                    try:
                        body = he.read().decode("utf-8", errors="replace")
                    except Exception:
                        pass
                    log_error("STT_HTTP", f"{m} HTTP {he.code}: {body[:300]}")
                    if he.code in (429, 503) and attempt == 0:
                        time.sleep(1.2)
                        continue
                    break
                except Exception as exc:
                    last_exc = exc
                    log_error("STT_EXC", exc)
                    break
        raise RuntimeError(f"Transcripción falló: {str(last_exc)[:50]}")

    def _listen_android_worker(self, seconds, was_bg, sample_rate=16000):
        wav_path = os.path.join(tempfile.gettempdir(), f"agrio_mic_{int(time.time() * 1000)}.wav")
        rec = None
        try:
            from jnius import autoclass  # type: ignore

            AudioRecord = autoclass("android.media.AudioRecord")
            MediaRecorder = autoclass("android.media.MediaRecorder")
            AudioFormat = autoclass("android.media.AudioFormat")

            min_buf = AudioRecord.getMinBufferSize(
                sample_rate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT
            )
            if min_buf is None or int(min_buf) <= 0:
                raise RuntimeError("Micrófono no soportado")

            rec = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                sample_rate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                max(int(min_buf), sample_rate * 2),
            )
            if rec.getState() != AudioRecord.STATE_INITIALIZED:
                raise RuntimeError(
                    "Sin permiso de micrófono: actívalo en Ajustes > Apps > Pydroid 3"
                )

            rec.startRecording()
            data = bytearray()
            buf = bytearray(4096)
            end_ts = time.time() + float(seconds)
            while time.time() < end_ts:
                n = rec.read(buf, 0, len(buf))
                if n is None or int(n) < 0:
                    raise RuntimeError("Error leyendo el micrófono")
                if n > 0:
                    data.extend(buf[: int(n)])
            try:
                rec.stop()
            except Exception:
                pass

            if not data or not any(data):
                raise RuntimeError("Audio vacío (revisa permiso de micrófono)")

            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(bytes(data))

            self._emit_phase("Transcribiendo")
            text = self._transcribe_with_gemini(wav_path)
            print(f"[ANDROID VOZ]: {text}", flush=True)

            def _ok(*_):
                if text and callable(self.on_result):
                    self.on_result(text, was_bg)
                elif callable(self.on_error):
                    self.on_error("No entendí lo que dijiste", was_bg)
                self._finish_cycle()

            Clock.schedule_once(_ok, 0)
        except Exception as exc:
            log_error("MIC_ANDROID_REC", exc)
            msg = str(exc).strip()[:70] or "Error con el micrófono"

            def _fail(*_, m=msg):
                if callable(self.on_error):
                    self.on_error(m, was_bg)
                self._finish_cycle()

            Clock.schedule_once(_fail, 0)
        finally:
            try:
                if rec is not None:
                    rec.release()
            except Exception:
                pass
            try:
                if os.path.exists(wav_path):
                    os.remove(wav_path)
            except Exception:
                pass

    def _listen_pc_worker(self, seconds=PC_ACTIVE_LISTEN_SECONDS, was_bg=False, samplerate=16000):
        wav_path = os.path.join(tempfile.gettempdir(), f"agrio_mic_{int(time.time() * 1000)}.wav")
        try:
            audio = self._sd.rec(
                int(seconds * samplerate), samplerate=samplerate, channels=1, dtype="int16"
            )
            self._sd.wait()
            self._wav_write(wav_path, samplerate, audio)

            recognizer = self._sr.Recognizer()
            with self._sr.AudioFile(wav_path) as source:
                recorded = recognizer.record(source)

            text = recognizer.recognize_google(recorded, language="es-MX").strip()
            print(f"[VOZ CAPTADA] ({'scan' if was_bg else 'activa'}): {text}", flush=True)

            def _ok(*_):
                if text and callable(self.on_result):
                    self.on_result(text, was_bg)
                elif callable(self.on_error):
                    self.on_error("No entendí lo que dijiste", was_bg)
                self._finish_cycle()

            Clock.schedule_once(_ok, 0)
        except Exception as exc:
            err_txt = str(exc)
            if "UnknownValueError" not in err_txt:
                log_error("MIC_PC", exc)

            def _fail(*_):
                if callable(self.on_error):
                    if "UnknownValueError" in err_txt or "recognition" in err_txt.lower():
                        self.on_error("No entendí lo que dijiste", was_bg)
                    else:
                        self.on_error("Error con el micrófono", was_bg)
                self._finish_cycle()

            Clock.schedule_once(_fail, 0)
        finally:
            try:
                if os.path.exists(wav_path):
                    os.remove(wav_path)
            except Exception:
                pass

    def listen_once(self, seconds=PC_ACTIVE_LISTEN_SECONDS, background_scan=False):
        try:
            if self._waiting_result:
                return False
            if self.mode == "none":
                self._init_backends()
            if not self.available or self.mode == "none":
                if callable(self.on_error):
                    self.on_error("Micrófono no disponible", background_scan)
                self._finish_cycle()
                return False

            self.is_background_scan = bool(background_scan)
            self._waiting_result = True
            self.is_listening = True

            if self._watchdog_ev:
                try:
                    self._watchdog_ev.cancel()
                except Exception:
                    pass
            extra = 30.0 if self.mode == "android" else 4.5
            self._watchdog_ev = Clock.schedule_once(
                lambda *_: self._finish_cycle(), float(seconds) + extra
            )

            target = (
                self._listen_android_worker if self.mode == "android" else self._listen_pc_worker
            )
            try:
                threading.Thread(
                    target=target,
                    kwargs={"seconds": float(seconds), "was_bg": bool(background_scan)},
                    daemon=True,
                ).start()
                return True
            except Exception as exc:
                log_error("MIC_THREAD", exc)
                self._finish_cycle()
                return False
        except Exception as exc:
            log_error("LISTEN_ONCE", exc)
            self._finish_cycle()
            return False


class AgrioVoice:
    """Motor de voz para Agrio con soporte gTTS + SoundLoader, pyttsx3 y respaldo WAV."""

    def __init__(self, on_speech_start=None, on_speech_end=None):
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self._lock = threading.Lock()
        self._current_sound = None
        self._gtts_cls = None
        self._pyttsx3 = None
        self.is_speaking = False

        try:
            from gtts import gTTS  # type: ignore

            self._gtts_cls = gTTS
        except Exception:
            self._gtts_cls = None

        if self._gtts_cls is None:
            try:
                import pyttsx3  # type: ignore

                self._pyttsx3 = pyttsx3
            except Exception:
                self._pyttsx3 = None

    def _build_syllable_wav(self, text, out_path):
        sample_rate = 16000
        words = [w for w in text.split() if w]
        syllable_count = max(2, min(14, sum(max(1, len(w) // 2) for w in words)))
        syl_dur = 0.13
        gap_dur = 0.035

        frames = bytearray()
        vowels = [(730, 1090), (530, 1840), (270, 2290), (570, 840), (300, 870)]

        for idx in range(syllable_count):
            f1, f2 = vowels[idx % len(vowels)]
            pitch = 165 + (idx % 3) * 18
            n_syl = int(sample_rate * syl_dur)
            for i in range(n_syl):
                t = i / sample_rate
                env = math.sin(math.pi * (i / n_syl))
                s = (
                    0.55 * math.sin(2 * math.pi * pitch * t)
                    + 0.30 * math.sin(2 * math.pi * f1 * t)
                    + 0.15 * math.sin(2 * math.pi * f2 * t)
                )
                val = int(max(-1.0, min(1.0, s * env)) * 22000)
                frames.extend(struct.pack("<h", val))

            n_gap = int(sample_rate * gap_dur)
            frames.extend(b"\x00\x00" * n_gap)

        with wave.open(out_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(frames)

        return syllable_count * (syl_dur + gap_dur)

    def _release_current_sound(self):
        try:
            if self._current_sound:
                try:
                    self._current_sound.stop()
                except Exception:
                    pass
                try:
                    self._current_sound.unload()
                except Exception:
                    pass
                self._current_sound = None
        except Exception:
            pass

    def _play_with_kivy(self, audio_path, volume_pct, fallback_duration):
        def _start_on_main(*_):
            try:
                self._release_current_sound()
                snd = SoundLoader.load(audio_path)
                if snd is None:
                    self.is_speaking = False
                    if callable(self.on_speech_end):
                        self.on_speech_end()
                    return

                self._current_sound = snd
                self.is_speaking = True
                snd.volume = max(0.05, min(1.0, int(volume_pct) / 100.0))
                dur = snd.length if (snd.length and snd.length > 0.1) else fallback_duration

                if callable(self.on_speech_start):
                    self.on_speech_start(dur)

                def _on_stop(*_a):
                    self.is_speaking = False
                    Clock.schedule_once(lambda *_: self._release_current_sound(), 0.15)
                    if callable(self.on_speech_end):
                        self.on_speech_end()

                snd.bind(on_stop=_on_stop)
                snd.play()
            except Exception as exc:
                log_error("VOICE_PLAY", exc)
                self.is_speaking = False
                if callable(self.on_speech_end):
                    self.on_speech_end()

        Clock.schedule_once(_start_on_main, 0)

    def speak(self, text, volume_pct=90, speech_rate=168):
        clean = (text or "").strip()
        if not clean:
            return

        est_duration = max(0.85, min(6.5, len(clean) * 0.065))

        def _worker():
            acquired = False
            try:
                acquired = self._lock.acquire(timeout=2.5)
                if not acquired:
                    return
                if self._gtts_cls is not None:
                    mp3_path = os.path.join(
                        tempfile.gettempdir(), f"agrio_tts_{int(time.time() * 1000)}.mp3"
                    )
                    try:
                        tts = self._gtts_cls(text=clean, lang="es", tld="com.mx")
                        tts.save(mp3_path)
                        self._play_with_kivy(mp3_path, volume_pct, est_duration)
                        return
                    except Exception as exc:
                        log_error("VOICE_GTTS", exc)

                if self._pyttsx3 is not None:
                    self.is_speaking = True
                    Clock.schedule_once(
                        lambda *_: self.on_speech_start(est_duration)
                        if callable(self.on_speech_start)
                        else None,
                        0,
                    )
                    try:
                        engine = self._pyttsx3.init()
                        engine.setProperty(
                            "volume", max(0.05, min(1.0, int(volume_pct) / 100.0))
                        )
                        engine.setProperty("rate", max(110, min(230, int(speech_rate))))
                        engine.say(clean)
                        engine.runAndWait()
                        engine.stop()
                    except Exception as exc:
                        log_error("VOICE_PYTTSX3", exc)
                    finally:
                        self.is_speaking = False
                        Clock.schedule_once(
                            lambda *_: self.on_speech_end()
                            if callable(self.on_speech_end)
                            else None,
                            0,
                        )
                    return

                wav_path = os.path.join(
                    tempfile.gettempdir(), f"agrio_vox_{int(time.time() * 1000)}.wav"
                )
                try:
                    dur = self._build_syllable_wav(clean, wav_path)
                    self._play_with_kivy(wav_path, volume_pct, dur)
                except Exception as exc:
                    log_error("VOICE_WAV", exc)
                    self.is_speaking = False
                    Clock.schedule_once(
                        lambda *_: self.on_speech_end()
                        if callable(self.on_speech_end)
                        else None,
                        0,
                    )
            except Exception as exc:
                log_error("VOICE_WORKER", exc)
                self.is_speaking = False
            finally:
                if acquired:
                    try:
                        self._lock.release()
                    except Exception:
                        pass

        try:
            threading.Thread(target=_worker, daemon=True).start()
        except Exception as exc:
            log_error("VOICE_THREAD", exc)
            self.is_speaking = False


class AgrioStore:
    def __init__(self, path=DATA_FILE):
        self.path = path
        self.data = {
            "volume": 90,
            "speech_rate": 168,
            "response_style": "Corto",
            "voice_enabled": True,
            "auto_scan_enabled": False,
            "listen_seconds": int(PC_ACTIVE_LISTEN_SECONDS),
            "accent_name": "Lima",
            "telegram_token": DEFAULT_TELEGRAM_TOKEN,
            "telegram_chat_id": DEFAULT_TELEGRAM_CHAT_ID,
            "tavily_api_key": "",
            "gemini_api_key": "",
            "gemini_model": DEFAULT_GEMINI_MODEL,
            "reminders": [],
        }
        self.load()
        if not str(self.data.get("gemini_model") or "").strip():
            self.data["gemini_model"] = DEFAULT_GEMINI_MODEL
        if not isinstance(self.data.get("reminders"), list):
            self.data["reminders"] = []
        self.apply_to_env()
        self.save()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.data.update(loaded)
            except Exception as exc:
                log_error("STORE_LOAD", exc)

    def apply_to_env(self):
        tok = str(self.data.get("telegram_token") or "").strip()
        cid = str(self.data.get("telegram_chat_id") or "").strip()
        if tok:
            os.environ["XIAOZHI_TELEGRAM_BOT_TOKEN"] = tok
        if cid:
            os.environ["XIAOZHI_TELEGRAM_CHAT_ID"] = cid
        if self.data.get("tavily_api_key"):
            os.environ["XIAOZHI_TAVILY_API_KEY"] = str(self.data["tavily_api_key"]).strip()
        if str(self.data.get("gemini_api_key") or "").strip():
            os.environ["GEMINI_API_KEY"] = str(self.data["gemini_api_key"]).strip()

    def save(self):
        self.apply_to_env()
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            log_error("STORE_SAVE", exc)


class MicStatusBadge(Widget):
    is_listening = NumericProperty(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.redraw, size=self.redraw, is_listening=self.redraw)
        Clock.schedule_once(lambda *_: self.redraw(), 0.05)

    def redraw(self, *args):
        try:
            self.canvas.clear()
            listening = bool(float(self.is_listening) > 0.5)
            r, g, b = (0.16, 0.92, 0.36) if listening else (0.95, 0.22, 0.24)
            rad = float(dp(6.5))
            cx = float(self.x) + rad + float(dp(4.0))
            cy = float(self.center_y)

            with self.canvas:
                Color(r, g, b, 0.24)
                Ellipse(pos=(cx - rad * 1.45, cy - rad * 1.45), size=(rad * 2.9, rad * 2.9))
                Color(r, g, b, 1.0)
                Ellipse(pos=(cx - rad, cy - rad), size=(rad * 2.0, rad * 2.0))
        except Exception:
            pass


class ClickableMicBox(BoxLayout):
    def __init__(self, on_badge_tap=None, **kwargs):
        super().__init__(**kwargs)
        self.on_badge_tap = on_badge_tap

    def on_touch_down(self, touch):
        try:
            if self.collide_point(*touch.pos):
                if callable(self.on_badge_tap):
                    self.on_badge_tap()
                return True
        except Exception as exc:
            log_error("MIC_BOX_TOUCH", exc)
        return super().on_touch_down(touch)


class AgrioFace(Widget):
    accent_color = ListProperty([0.71, 1.0, 0.26, 1.0])
    bg_color = ListProperty([0.0, 0.0, 0.0, 1.0])
    blink = NumericProperty(1.0)
    mouth_open = NumericProperty(0.0)
    mood = "neutral"

    def __init__(self, on_face_touched=None, **kwargs):
        super().__init__(**kwargs)
        self.on_face_touched = on_face_touched
        self._face_rect = (0.0, 0.0, 0.0, 0.0)
        self._talk_ev = None
        self._talk_end_ev = None
        self._think_phase = 0.0

        self.bind(
            pos=self._trigger_redraw,
            size=self._trigger_redraw,
            blink=self._trigger_redraw,
            mouth_open=self._trigger_redraw,
            accent_color=self._trigger_redraw,
            bg_color=self._trigger_redraw,
        )
        Clock.schedule_interval(self._auto_blink, 2.8)
        Clock.schedule_interval(self._animate_gestures, 0.16)
        Clock.schedule_once(lambda *_: self.redraw(), 0.05)

    def set_mood(self, new_mood):
        try:
            self.mood = str(new_mood or "neutral")
            self.redraw()
        except Exception:
            pass

    def _animate_gestures(self, dt):
        try:
            if self.mood == "thinking":
                self._think_phase += 0.45
                self.redraw()
        except Exception:
            pass

    def _trigger_redraw(self, *args):
        self.redraw()

    def start_talking_mouth(self, duration_sec=2.0):
        try:
            self.stop_talking_mouth()
            self.mouth_open = 0.75

            def _step_mouth(dt):
                self.mouth_open = random.uniform(0.2, 1.0)

            self._talk_ev = Clock.schedule_interval(_step_mouth, 0.075)
            self._talk_end_ev = Clock.schedule_once(
                lambda *_: self.stop_talking_mouth(), max(0.5, float(duration_sec))
            )
        except Exception:
            pass

    def stop_talking_mouth(self):
        if self._talk_ev:
            try:
                self._talk_ev.cancel()
            except Exception:
                pass
            self._talk_ev = None
        if self._talk_end_ev:
            try:
                self._talk_end_ev.cancel()
            except Exception:
                pass
            self._talk_end_ev = None
        self.mouth_open = 0.0

    def _auto_blink(self, dt):
        try:
            if self.mood == "sleeping":
                return
            self.blink = 0.12
            Clock.schedule_once(lambda *_: setattr(self, "blink", 1.0), 0.14)
        except Exception:
            pass

    def _compute_face_box(self):
        w = max(float(self.width), float(Window.width), 300.0)
        h = max(float(self.height), float(Window.height), 300.0)
        cx = float(self.center_x) if self.width > 0 else w / 2.0
        cy = float(self.center_y) if self.height > 0 else h / 2.0

        usable_w = max(180.0, w - float(dp(36)))
        usable_h = max(180.0, h - float(dp(120)))
        raw_size = max(float(dp(180)), min(usable_w, usable_h))
        box_size = max(float(dp(135)), raw_size * 0.75)

        bx = cx - box_size / 2.0
        by = cy - box_size / 2.0 + float(dp(8.0))
        self._face_rect = (bx, by, box_size, box_size)
        return bx, by, box_size, cx, cy

    def _is_inside_face(self, x, y):
        bx, by, bw, bh = self._face_rect
        return bx <= x <= (bx + bw) and by <= y <= (by + bh)

    def on_touch_down(self, touch):
        try:
            if self._is_inside_face(*touch.pos):
                self.blink = 0.25
                Clock.schedule_once(lambda *_: setattr(self, "blink", 1.0), 0.12)
                if callable(self.on_face_touched):
                    self.on_face_touched(touch.pos)
                return True
        except Exception as exc:
            log_error("FACE_TOUCH", exc)
        return super().on_touch_down(touch)

    def redraw(self, *args):
        try:
            self.canvas.clear()
            bx, by, box_size, cx, cy = self._compute_face_box()
            r_acc, g_acc, b_acc, a_acc = _rgba(self.accent_color)
            r_bg, g_bg, b_bg, a_bg = _rgba(self.bg_color)
            full_w = max(float(self.width), float(Window.width))
            full_h = max(float(self.height), float(Window.height))
            stroke_w = max(float(dp(4.0)), box_size * 0.016)

            with self.canvas:
                Color(r_bg, g_bg, b_bg, a_bg)
                Rectangle(pos=(0.0, 0.0), size=(full_w, full_h))

                Color(r_acc, g_acc, b_acc, a_acc)
                Line(
                    rounded_rectangle=(bx, by, box_size, box_size, float(dp(34))),
                    width=stroke_w,
                )

                eye_w = box_size * 0.16
                eye_scale = float(self.blink)
                if self.mood == "surprised":
                    eye_w = box_size * 0.18
                    eye_scale = max(eye_scale, 1.15)
                elif self.mood == "focused":
                    eye_scale = min(eye_scale, 0.65)

                eye_h = max(float(dp(4.5)), box_size * 0.23 * eye_scale)
                eye_y = by + box_size * 0.62 - eye_h / 2.0
                shift_x = (
                    math.sin(self._think_phase) * box_size * 0.04
                    if self.mood == "thinking"
                    else 0.0
                )
                left_eye_x = bx + box_size * 0.28 - eye_w / 2.0 + shift_x
                right_eye_x = bx + box_size * 0.72 - eye_w / 2.0 + shift_x

                if self.mood == "sleeping":
                    Line(
                        points=[
                            left_eye_x,
                            eye_y + eye_h / 2.0,
                            left_eye_x + eye_w,
                            eye_y + eye_h / 2.0,
                        ],
                        width=stroke_w,
                    )
                    Line(
                        points=[
                            right_eye_x,
                            eye_y + eye_h / 2.0,
                            right_eye_x + eye_w,
                            eye_y + eye_h / 2.0,
                        ],
                        width=stroke_w,
                    )
                elif self.mood == "surprised":
                    Line(
                        circle=(left_eye_x + eye_w / 2.0, eye_y + eye_h / 2.0, eye_w * 0.52),
                        width=stroke_w * 0.9,
                    )
                    Line(
                        circle=(right_eye_x + eye_w / 2.0, eye_y + eye_h / 2.0, eye_w * 0.52),
                        width=stroke_w * 0.9,
                    )
                else:
                    Rectangle(pos=(left_eye_x, eye_y), size=(eye_w, eye_h))
                    Rectangle(pos=(right_eye_x, eye_y), size=(eye_w, eye_h))

                if self.mood == "annoyed":
                    brow_y = eye_y + eye_h + float(dp(8.0))
                    Line(
                        points=[
                            left_eye_x - float(dp(3.0)),
                            brow_y + float(dp(8.0)),
                            left_eye_x + eye_w + float(dp(3.0)),
                            brow_y - float(dp(2.0)),
                        ],
                        width=stroke_w * 0.85,
                    )
                    Line(
                        points=[
                            right_eye_x - float(dp(3.0)),
                            brow_y - float(dp(2.0)),
                            right_eye_x + eye_w + float(dp(3.0)),
                            brow_y + float(dp(8.0)),
                        ],
                        width=stroke_w * 0.85,
                    )
                elif self.mood == "thinking":
                    brow_y = eye_y + eye_h + float(dp(8.0))
                    Line(
                        points=[
                            left_eye_x,
                            brow_y,
                            left_eye_x + eye_w,
                            brow_y + float(dp(3.0)),
                        ],
                        width=stroke_w * 0.75,
                    )
                    Line(
                        points=[
                            right_eye_x,
                            brow_y + float(dp(7.0)),
                            right_eye_x + eye_w,
                            brow_y + float(dp(9.0)),
                        ],
                        width=stroke_w * 0.75,
                    )
                elif self.mood == "focused":
                    brow_y = eye_y + eye_h + float(dp(6.0))
                    Line(
                        points=[left_eye_x, brow_y, left_eye_x + eye_w, brow_y],
                        width=stroke_w * 0.8,
                    )
                    Line(
                        points=[right_eye_x, brow_y, right_eye_x + eye_w, brow_y],
                        width=stroke_w * 0.8,
                    )

                mouth_w = box_size * 0.42
                mouth_x = cx - mouth_w / 2.0
                mouth_y = by + box_size * 0.24

                if float(self.mouth_open) > 0.05 and self.mood != "sleeping":
                    open_h = max(float(dp(9.0)), box_size * 0.04) + box_size * 0.11 * float(
                        self.mouth_open
                    )
                    open_w = max(float(dp(24.0)), box_size * 0.09) + box_size * 0.07 * float(
                        self.mouth_open
                    )
                    Ellipse(
                        pos=(cx - open_w / 2.0, mouth_y - open_h / 2.0),
                        size=(open_w, open_h),
                    )
                elif self.mood == "listening":
                    Line(
                        circle=(
                            cx,
                            mouth_y + float(dp(2.0)),
                            max(float(dp(12.0)), box_size * 0.045),
                        ),
                        width=stroke_w * 0.8,
                    )
                elif self.mood == "surprised":
                    Line(
                        circle=(
                            cx,
                            mouth_y + float(dp(2.0)),
                            max(float(dp(14.0)), box_size * 0.055),
                        ),
                        width=stroke_w * 0.85,
                    )
                elif self.mood == "thinking":
                    wave_dx = math.sin(self._think_phase) * box_size * 0.05
                    Line(
                        points=[
                            mouth_x + wave_dx,
                            mouth_y,
                            cx + wave_dx,
                            mouth_y + float(dp(4.0)),
                            mouth_x + mouth_w + wave_dx,
                            mouth_y - float(dp(2.0)),
                        ],
                        width=stroke_w * 0.8,
                    )
                elif self.mood == "focused":
                    Line(
                        points=[
                            mouth_x + box_size * 0.05,
                            mouth_y,
                            mouth_x + mouth_w - box_size * 0.05,
                            mouth_y,
                        ],
                        width=stroke_w * 0.85,
                    )
                elif self.mood == "sleeping":
                    Line(
                        circle=(
                            cx,
                            mouth_y + float(dp(2.0)),
                            max(float(dp(7.0)), box_size * 0.025),
                        ),
                        width=stroke_w * 0.75,
                    )
                elif self.mood == "happy":
                    Line(
                        bezier=[
                            mouth_x,
                            mouth_y + float(dp(6.0)),
                            cx,
                            mouth_y - max(float(dp(12.0)), box_size * 0.05),
                            mouth_x + mouth_w,
                            mouth_y + float(dp(6.0)),
                        ],
                        width=stroke_w * 0.85,
                    )
                elif self.mood == "annoyed":
                    Line(
                        bezier=[
                            mouth_x,
                            mouth_y - float(dp(7.0)),
                            cx,
                            mouth_y + max(float(dp(8.0)), box_size * 0.03),
                            mouth_x + mouth_w,
                            mouth_y - float(dp(7.0)),
                        ],
                        width=stroke_w * 0.85,
                    )
                else:
                    Line(
                        points=[
                            mouth_x,
                            mouth_y,
                            cx,
                            mouth_y - max(float(dp(6.0)), box_size * 0.022),
                            mouth_x + mouth_w,
                            mouth_y,
                        ],
                        width=stroke_w * 0.8,
                    )
        except Exception as exc:
            log_error("FACE_REDRAW", exc)


class AgrioFaceOnlyRoot(FloatLayout):
    """Asistente con escucha en Android (S24 Ultra / Pydroid 3) y PC, cálculo local y menú."""

    def __init__(self, store: AgrioStore, **kwargs):
        super().__init__(**kwargs)
        Window.clearcolor = (0.0, 0.0, 0.0, 1.0)
        self.store = store
        self.remaining_sec = 0
        self.initial_sec = POMODORO_SECONDS
        self._timer_ev = None
        self._loop_listen_ev = None
        self._reminder_ev = None
        self._cleanup_ev = None
        self._settings_popup = None
        self._cmd_popup = None
        self._mic_error_streak = 0
        self._backoff_until = 0.0
        self._gemini_busy = False
        self._chat_history = []
        self._last_ai_reply = ""
        self._manual_listen_mode = False

        self._touch_index = 0
        self._rapid_taps = 0
        self._last_tap_ts = 0.0
        self._menu_tap_count = 0
        self._last_menu_tap_ts = 0.0

        init_accent = ACCENT_PRESETS.get(
            self.store.data.get("accent_name", "Lima"), ACCENT_PRESETS["Lima"]
        )

        self.face = AgrioFace(
            on_face_touched=self.handle_face_touch,
            accent_color=init_accent,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.add_widget(self.face)

        self.timer_badge = Button(
            text="Menú",
            font_size=dp(12),
            bold=True,
            color=_rgba(init_accent),
            background_color=(0.12, 0.12, 0.15, 0.85),
            size_hint=(None, None),
            size=(dp(145), dp(30)),
            pos_hint={"x": 0.03, "top": 0.98},
        )
        self.timer_badge.bind(on_release=lambda *_: self._handle_menu_badge_tap())
        self.add_widget(self.timer_badge)

        self.mic_indicator_box = ClickableMicBox(
            on_badge_tap=self.handle_mic_badge_touch,
            orientation="horizontal",
            size_hint=(None, None),
            size=(dp(188), dp(30)),
            pos_hint={"right": 0.98, "top": 0.98},
            padding=(dp(4), dp(2)),
            spacing=dp(4),
        )
        self.mic_dot = MicStatusBadge(size_hint=(None, 1), width=dp(22))
        self.mic_label = Label(
            text="Toca para hablar",
            font_size=dp(12),
            bold=True,
            color=(0.95, 0.30, 0.32, 1.0),
            halign="left",
            valign="middle",
        )
        self.mic_label.bind(size=self.mic_label.setter("text_size"))
        self.mic_indicator_box.add_widget(self.mic_dot)
        self.mic_indicator_box.add_widget(self.mic_label)
        self.add_widget(self.mic_indicator_box)

        self.caption = Label(
            text="",
            font_size=dp(16),
            bold=True,
            color=(1.0, 1.0, 1.0, 1.0),
            size_hint=(0.94, None),
            height=dp(92),
            pos_hint={"center_x": 0.5, "y": 0.03},
            halign="center",
            valign="middle",
        )
        self.caption.bind(size=self.caption.setter("text_size"))
        self.add_widget(self.caption)

        self.voice = AgrioVoice(
            on_speech_start=self._on_voice_start,
            on_speech_end=self._on_voice_end,
        )
        self.listener = AgrioListener(
            on_result=self._on_heard_speech,
            on_error=self._on_listen_error,
            on_done=self._on_listen_done,
            on_phase=self._on_listen_phase,
            get_api_key=self._get_gemini_key,
            get_model=self._get_gemini_model,
        )

        Window.bind(on_key_down=self._on_window_key_down)
        self._update_mic_indicator(False)
        Clock.schedule_once(
            lambda *_: self._say_and_show(random.choice(GREETINGS), "happy", show_secs=4.5), 1.0
        )
        self._configure_auto_scan_timer()
        self._reminder_ev = Clock.schedule_interval(self._check_reminders_tick, 10.0)
        self._cleanup_ev = Clock.schedule_interval(lambda dt: _cleanup_old_temp_audio(120), 120.0)

    def _get_gemini_key(self):
        return (
            self.store.data.get("gemini_api_key")
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or ""
        )

    def _get_gemini_model(self):
        m = str(self.store.data.get("gemini_model") or DEFAULT_GEMINI_MODEL).strip()
        if m.startswith("models/"):
            m = m.split("/", 1)[1]
        return m

    def _on_listen_phase(self, text):
        try:
            self._update_mic_indicator(False, custom_status=text)
            if text == "Transcribiendo":
                self.face.set_mood("thinking")
        except Exception:
            pass

    def open_command_input_popup(self, voice_mode=False):
        if self._cmd_popup is not None:
            return
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        hint = (
            "Toca el micrófono del teclado y habla"
            if voice_mode
            else "Ej: hora, chiste, cuánto es 5 por 5, pomodoro..."
        )
        inp = TextInput(
            hint_text=hint,
            multiline=False,
            size_hint_y=None,
            height=dp(44),
        )
        row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        btn_cancel = Button(text="Cancelar", on_release=lambda *_: pop.dismiss())
        btn_send = Button(text="Enviar")
        row.add_widget(btn_cancel)
        row.add_widget(btn_send)
        box.add_widget(inp)
        box.add_widget(row)

        title = "Habla con Agrio (micrófono del teclado)" if voice_mode else "Comando para Agrio"
        pop = Popup(title=title, content=box, size_hint=(0.92, 0.36), pos_hint={"top": 0.98})
        self._cmd_popup = pop
        state = {"ev": None, "sent": False}

        def _send(*_):
            if state["sent"]:
                return
            txt = (inp.text or "").strip()
            if not txt:
                return
            state["sent"] = True
            if state["ev"]:
                state["ev"].cancel()
            pop.dismiss()
            self.handle_command(txt, require_wake=False)

        def _on_text(*_):
            if not voice_mode:
                return
            if state["ev"]:
                state["ev"].cancel()
            if (inp.text or "").strip():
                state["ev"] = Clock.schedule_once(_send, KEYBOARD_VOICE_IDLE_SECONDS)

        def _on_dismiss(*_):
            if state["ev"]:
                state["ev"].cancel()
            self._cmd_popup = None
            self._update_mic_indicator(False)
            if self.face.mood == "listening":
                self.face.set_mood("neutral")

        btn_send.bind(on_release=_send)
        inp.bind(on_text_validate=_send)
        inp.bind(text=_on_text)
        pop.bind(on_dismiss=_on_dismiss)
        pop.open()
        Clock.schedule_once(lambda *_: setattr(inp, "focus", True), 0.3)

    def _handle_menu_badge_tap(self):
        try:
            if self.listener.mode == "android":
                self.open_settings_menu()
                return
            now = time.monotonic()
            if now - self._last_menu_tap_ts < 0.8:
                self._menu_tap_count += 1
            else:
                self._menu_tap_count = 1
            self._last_menu_tap_ts = now
            if self._menu_tap_count >= 2:
                self._menu_tap_count = 0
                self.open_settings_menu()
        except Exception as exc:
            log_error("MENU_TAP", exc)

    def _get_listen_seconds(self):
        try:
            val = int(self.store.data.get("listen_seconds", PC_ACTIVE_LISTEN_SECONDS))
            return float(max(3, min(20, val)))
        except Exception:
            return PC_ACTIVE_LISTEN_SECONDS

    def _configure_auto_scan_timer(self):
        if self._loop_listen_ev:
            try:
                self._loop_listen_ev.cancel()
            except Exception:
                pass
            self._loop_listen_ev = None
        if self.listener.mode == "pc_mic" and bool(self.store.data.get("auto_scan_enabled", False)):
            self._loop_listen_ev = Clock.schedule_interval(self._wake_scan_tick, 5.2)

    def handle_mic_badge_touch(self):
        try:
            if self._gemini_busy:
                return
            if self.listener.mode == "android" and ANDROID_USE_KEYBOARD_DICTATION:
                if self.voice.is_speaking:
                    self.voice._release_current_sound()
                    self.voice.is_speaking = False
                    self.face.stop_talking_mouth()
                self.face.set_mood("listening")
                self._update_mic_indicator(True, active_text="Dicta con el teclado")
                self.open_command_input_popup(voice_mode=True)
                return
            if self.listener._waiting_result:
                return
            if self.voice.is_speaking:
                self.voice._release_current_sound()
                self.voice.is_speaking = False
                self.face.stop_talking_mouth()

            self._backoff_until = 0.0
            self._mic_error_streak = 0
            self._manual_listen_mode = True
            if self.face.mood == "sleeping":
                self.face.set_mood("neutral")
            self.face.set_mood("listening")
            secs = self._get_listen_seconds()
            self._update_mic_indicator(True, active_text=f"Habla ({int(secs)}s)...")
            started = self.listener.listen_once(seconds=secs, background_scan=False)
            if not started:
                self._manual_listen_mode = False
                self._update_mic_indicator(False)
        except Exception as exc:
            log_error("BADGE_LISTEN", exc)
            self._manual_listen_mode = False
            self._update_mic_indicator(False)

    def _update_mic_indicator(
        self, listening: bool, custom_status: str = "", active_text: str = ""
    ):
        try:
            active = bool(listening)
            self.mic_dot.is_listening = 1.0 if active else 0.0
            if custom_status:
                self.mic_label.text = custom_status
                self.mic_label.color = (0.35, 0.82, 1.0, 1.0)
            elif active:
                self.mic_label.text = active_text or "Escuchando"
                self.mic_label.color = (0.20, 0.95, 0.42, 1.0)
            else:
                self.mic_label.text = (
                    "Toca para hablar" if self.listener.mode == "android" else "No escucha"
                )
                self.mic_label.color = (0.95, 0.30, 0.32, 1.0)
        except Exception:
            pass

    def _on_window_key_down(self, window, key, scancode, codepoint, modifiers):
        try:
            if key in (27, 1001):
                if self._settings_popup is not None:
                    self._settings_popup.dismiss()
                    return True
                if self._cmd_popup is not None:
                    self._cmd_popup.dismiss()
                    return True
            has_ctrl = ("ctrl" in modifiers) or ("meta" in modifiers)
            cp_low = (codepoint or "").lower()
            if has_ctrl and (cp_low == "m" or key == 109):
                self.open_settings_menu()
                return True
            if has_ctrl and (cp_low == "l" or key == 108):
                self.handle_mic_badge_touch()
                return True
        except Exception as exc:
            log_error("KEY_DOWN", exc)
        return False

    def apply_accent_color(self, accent_name):
        try:
            name = accent_name if accent_name in ACCENT_PRESETS else "Lima"
            rgba = _rgba(ACCENT_PRESETS[name])
            self.store.data["accent_name"] = name
            self.store.save()
            self.face.accent_color = list(rgba)
            self.timer_badge.color = rgba
            self.face.redraw()
        except Exception as exc:
            log_error("ACCENT", exc)

    def open_settings_menu(self):
        if self._settings_popup is not None:
            return

        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        scroll = ScrollView()
        inner = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        inner.bind(minimum_height=inner.setter("height"))

        def _lbl(t, h=dp(24), bold=False):
            lb = Label(
                text=t,
                bold=bold,
                font_size=dp(14),
                halign="left",
                valign="middle",
                size_hint_y=None,
                height=h,
            )
            lb.bind(size=lb.setter("text_size"))
            return lb

        inner.add_widget(_lbl(f"Acciones rápidas (modo: {self.listener.mode})", bold=True))
        actions_grid = GridLayout(cols=3, size_hint_y=None, height=dp(78), spacing=dp(6))

        btn_act_listen = Button(text="Escuchar ahora")
        btn_act_cmd = Button(text="Escribir comando")
        btn_act_pomo_on = Button(text="Iniciar Pomodoro")
        btn_act_voice = Button(text="Probar voz")
        btn_act_clean = Button(text="Limpiar temp")
        btn_act_log = Button(text="Último error")

        for b in (
            btn_act_listen,
            btn_act_cmd,
            btn_act_pomo_on,
            btn_act_voice,
            btn_act_clean,
            btn_act_log,
        ):
            b.font_size = dp(12)
            actions_grid.add_widget(b)

        inner.add_widget(actions_grid)

        inner.add_widget(_lbl("Color de Agrio (14 colores)", bold=True))
        cur_accent = self.store.data.get("accent_name", "Lima")
        sp_color = Spinner(
            text=cur_accent if cur_accent in ACCENT_PRESETS else "Lima",
            values=tuple(ACCENT_PRESETS.keys()),
            size_hint_y=None,
            height=dp(40),
        )
        sp_color.bind(text=lambda _, val: self.apply_accent_color(val))
        inner.add_widget(sp_color)

        inner.add_widget(_lbl("Volumen (10-100), voz y escaneo automático", bold=True))
        vol_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        inp_vol = TextInput(
            text=str(self.store.data.get("volume", 90)),
            multiline=False,
            input_filter="int",
        )
        btn_voice_toggle = Button(
            text="Voz: ON" if self.store.data.get("voice_enabled", True) else "Voz: OFF",
            size_hint_x=None,
            width=dp(96),
        )
        btn_scan_toggle = Button(
            text="Auto: ON" if self.store.data.get("auto_scan_enabled", False) else "Auto: OFF",
            size_hint_x=None,
            width=dp(96),
        )

        def _toggle_v(*_):
            nxt = not bool(self.store.data.get("voice_enabled", True))
            self.store.data["voice_enabled"] = nxt
            self.store.save()
            btn_voice_toggle.text = "Voz: ON" if nxt else "Voz: OFF"

        def _toggle_scan(*_):
            nxt = not bool(self.store.data.get("auto_scan_enabled", False))
            self.store.data["auto_scan_enabled"] = nxt
            self.store.save()
            self._configure_auto_scan_timer()
            btn_scan_toggle.text = "Auto: ON" if nxt else "Auto: OFF"

        btn_voice_toggle.bind(on_release=_toggle_v)
        btn_scan_toggle.bind(on_release=_toggle_scan)
        vol_row.add_widget(inp_vol)
        vol_row.add_widget(btn_voice_toggle)
        vol_row.add_widget(btn_scan_toggle)
        inner.add_widget(vol_row)

        inner.add_widget(_lbl("Estilo Gemini, velocidad voz y seg. de escucha", bold=True))
        style_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        cur_style = str(self.store.data.get("response_style", "Corto"))
        sp_style = Spinner(
            text=cur_style if cur_style in ("Corto", "Detallado") else "Corto",
            values=("Corto", "Detallado"),
        )
        inp_rate = TextInput(
            text=str(self.store.data.get("speech_rate", 168)),
            hint_text="168",
            multiline=False,
            input_filter="int",
            size_hint_x=None,
            width=dp(82),
        )
        inp_listen_sec = TextInput(
            text=str(self.store.data.get("listen_seconds", int(PC_ACTIVE_LISTEN_SECONDS))),
            hint_text="8",
            multiline=False,
            input_filter="int",
            size_hint_x=None,
            width=dp(72),
        )
        style_row.add_widget(sp_style)
        style_row.add_widget(inp_rate)
        style_row.add_widget(inp_listen_sec)
        inner.add_widget(style_row)

        inner.add_widget(_lbl("Gemini API Key (para 'Agrio' y para entender tu voz)", bold=True))
        inp_gemini = TextInput(
            text=str(self.store.data.get("gemini_api_key", "")),
            hint_text="AIza...",
            multiline=False,
            size_hint_y=None,
            height=dp(40),
        )
        inner.add_widget(inp_gemini)

        inner.add_widget(_lbl("Modelo de Gemini (selector rápido o nombre manual)", bold=True))
        cur_model = str(self.store.data.get("gemini_model") or DEFAULT_GEMINI_MODEL).strip()
        model_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        sp_model = Spinner(
            text=cur_model if cur_model in GEMINI_MODEL_OPTIONS else GEMINI_MODEL_OPTIONS[0],
            values=GEMINI_MODEL_OPTIONS,
            size_hint_x=0.52,
        )
        inp_model = TextInput(
            text=cur_model,
            hint_text="gemini-2.5-flash",
            multiline=False,
            size_hint_x=0.48,
        )
        sp_model.bind(text=lambda _, val: setattr(inp_model, "text", val))
        model_row.add_widget(sp_model)
        model_row.add_widget(inp_model)
        inner.add_widget(model_row)

        test_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        btn_test_gemini = Button(text="Probar Gemini ahora", size_hint_x=0.42)
        lbl_test_status = Label(
            text="Listo para probar",
            font_size=dp(11),
            halign="left",
            valign="middle",
            size_hint_x=0.58,
        )
        lbl_test_status.bind(size=lbl_test_status.setter("text_size"))
        test_row.add_widget(btn_test_gemini)
        test_row.add_widget(lbl_test_status)
        inner.add_widget(test_row)

        inner.add_widget(_lbl("Telegram Bot Token", bold=True))
        inp_tg_token = TextInput(
            text=str(self.store.data.get("telegram_token", "")),
            hint_text="123456789:AA...",
            multiline=False,
            size_hint_y=None,
            height=dp(40),
        )
        inner.add_widget(_lbl("Telegram Chat ID", bold=True))
        inp_tg_chat = TextInput(
            text=str(self.store.data.get("telegram_chat_id", "")),
            hint_text="Tu chat id numérico",
            multiline=False,
            size_hint_y=None,
            height=dp(40),
        )
        inner.add_widget(inp_tg_token)
        inner.add_widget(inp_tg_chat)

        inner.add_widget(_lbl("Tavily API Key (opcional)", bold=True))
        inp_tavily = TextInput(
            text=str(self.store.data.get("tavily_api_key", "")),
            hint_text="tvly-...",
            multiline=False,
            size_hint_y=None,
            height=dp(40),
        )
        inner.add_widget(inp_tavily)

        scroll.add_widget(inner)
        box.add_widget(scroll)

        btns = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        btn_close = Button(text="Cerrar", on_release=lambda *_: pop.dismiss())
        btn_save = Button(text="Guardar")
        btns.add_widget(btn_close)
        btns.add_widget(btn_save)
        box.add_widget(btns)

        pop = Popup(title="Configuración de Agrio", content=box, size_hint=(0.94, 0.92))
        self._settings_popup = pop

        def _act_listen(*_):
            pop.dismiss()
            Clock.schedule_once(lambda *_: self.handle_mic_badge_touch(), 0.25)

        def _act_cmd(*_):
            pop.dismiss()
            Clock.schedule_once(lambda *_: self.open_command_input_popup(), 0.2)

        def _act_pomo_on(*_):
            pop.dismiss()
            self.start_timer(POMODORO_SECONDS, "Pomodoro")

        def _act_voice(*_):
            self._say_and_show("Prueba de voz de Agrio funcionando", mood="happy", show_secs=4.5)

        def _act_clean(*_):
            n_del = _cleanup_old_temp_audio(0)
            lbl_test_status.text = f"Temporales limpiados: {n_del}"

        def _act_log(*_):
            lbl_test_status.text = read_last_error_summary()

        btn_act_listen.bind(on_release=_act_listen)
        btn_act_cmd.bind(on_release=_act_cmd)
        btn_act_pomo_on.bind(on_release=_act_pomo_on)
        btn_act_voice.bind(on_release=_act_voice)
        btn_act_clean.bind(on_release=_act_clean)
        btn_act_log.bind(on_release=_act_log)

        def _test_gem(*_):
            test_key = "".join(str(inp_gemini.text or "").split())
            if not test_key:
                lbl_test_status.text = "Falta Gemini API Key"
                return
            chosen_m = (inp_model.text or sp_model.text or DEFAULT_GEMINI_MODEL).strip()
            if chosen_m.startswith("models/"):
                chosen_m = chosen_m.split("/", 1)[1]
            lbl_test_status.text = f"Probando {chosen_m}..."

            def _ping():
                try:
                    ok_txt = _gemini_generate(
                        test_key,
                        chosen_m,
                        [{"text": "Di solo OK."}],
                        max_tokens=12,
                        temperature=0.2,
                        timeout=12,
                    )
                    msg = f"OK ({chosen_m}): {ok_txt[:28]}" if ok_txt else "OK"
                    Clock.schedule_once(lambda *_, m=msg: setattr(lbl_test_status, "text", m), 0)
                except urllib.error.HTTPError as he:
                    Clock.schedule_once(
                        lambda *_, code=he.code: setattr(
                            lbl_test_status, "text", f"Error HTTP {code} en {chosen_m}"
                        ),
                        0,
                    )
                except Exception as exc:
                    short = str(exc).strip()[:32] or "red"
                    Clock.schedule_once(
                        lambda *_, s=short: setattr(lbl_test_status, "text", f"Fallo: {s}"), 0
                    )

            threading.Thread(target=_ping, daemon=True).start()

        btn_test_gemini.bind(on_release=_test_gem)

        def _on_dismiss(*_):
            self._settings_popup = None

        def _save(*_):
            raw_v = inp_vol.text.strip()
            if raw_v.isdigit():
                self.store.data["volume"] = max(10, min(100, int(raw_v)))
            raw_r = inp_rate.text.strip()
            if raw_r.isdigit():
                self.store.data["speech_rate"] = max(110, min(230, int(raw_r)))
            raw_ls = inp_listen_sec.text.strip()
            if raw_ls.isdigit():
                self.store.data["listen_seconds"] = max(3, min(20, int(raw_ls)))
            chosen_model = (inp_model.text or sp_model.text or DEFAULT_GEMINI_MODEL).strip()
            if chosen_model.startswith("models/"):
                chosen_model = chosen_model.split("/", 1)[1]
            self.store.data["response_style"] = sp_style.text
            self.store.data["accent_name"] = sp_color.text
            self.store.data["gemini_api_key"] = inp_gemini.text.strip()
            self.store.data["gemini_model"] = chosen_model or DEFAULT_GEMINI_MODEL
            self.store.data["telegram_token"] = inp_tg_token.text.strip()
            self.store.data["telegram_chat_id"] = inp_tg_chat.text.strip()
            self.store.data["tavily_api_key"] = inp_tavily.text.strip()
            self.store.save()
            self._configure_auto_scan_timer()
            self.apply_accent_color(sp_color.text)
            pop.dismiss()
            self._say_and_show("Configuración guardada", mood="happy", show_secs=4.0)

        btn_save.bind(on_release=_save)
        pop.bind(on_dismiss=_on_dismiss)
        pop.open()

    def _show_caption(self, msg, secs=5.0):
        try:
            self.caption.text = str(msg or "")
            Clock.unschedule(self._clear_caption)
            if secs:
                Clock.schedule_once(self._clear_caption, secs)
        except Exception:
            pass

    def _clear_caption(self, *args):
        try:
            self.caption.text = ""
        except Exception:
            pass

    def _on_voice_start(self, duration_sec):
        try:
            self._update_mic_indicator(False, custom_status="Hablando")
            if self.face.mood != "sleeping":
                self.face.set_mood("speaking")
            self.face.start_talking_mouth(duration_sec)
        except Exception:
            pass

    def _on_voice_end(self):
        try:
            self.face.stop_talking_mouth()
            if self.face.mood == "speaking":
                self.face.set_mood("neutral")
            if self.listener.is_listening:
                lbl = (
                    "Escuchando ('hey tú')"
                    if self.listener.is_background_scan
                    else f"Escuchando ({int(self._get_listen_seconds())}s)"
                )
                self._update_mic_indicator(True, active_text=lbl)
            else:
                self._update_mic_indicator(False)
        except Exception:
            pass

    def _say_and_show(self, phrase, mood="speaking", show_secs=5.0):
        try:
            txt = str(phrase or "").strip()
            if not txt:
                return
            if mood != "sleeping":
                self.face.set_mood(mood)
            self._show_caption(txt, secs=max(4.5, float(show_secs)))
            if self.store.data.get("voice_enabled", True):
                self.voice.speak(
                    txt,
                    volume_pct=self.store.data.get("volume", 90),
                    speech_rate=self.store.data.get("speech_rate", 168),
                )
        except Exception as exc:
            log_error("SAY_AND_SHOW", exc)

    def _wake_scan_tick(self, dt):
        try:
            if not bool(self.store.data.get("auto_scan_enabled", False)):
                return
            if time.monotonic() < self._backoff_until:
                self._update_mic_indicator(False)
                return
            if (
                self.voice.is_speaking
                or self.listener._waiting_result
                or self._gemini_busy
                or self.face.mood == "sleeping"
            ):
                return
            if self.listener.mode == "pc_mic" and self.listener.available:
                self._manual_listen_mode = False
                started = self.listener.listen_once(
                    seconds=PC_WAKE_SCAN_SECONDS, background_scan=True
                )
                self._update_mic_indicator(
                    bool(started), active_text="Escuchando ('hey tú')" if started else ""
                )
        except Exception as exc:
            log_error("WAKE_SCAN", exc)
            self._update_mic_indicator(False)

    def _on_listen_done(self, was_bg=False):
        try:
            self._manual_listen_mode = False
            if not self.voice.is_speaking and not self._gemini_busy:
                self._update_mic_indicator(False)
            if not self.voice.is_speaking and self.face.mood in ("listening",):
                self.face.set_mood("neutral")
        except Exception:
            pass

    def _on_listen_error(self, err, was_bg=False):
        try:
            self._manual_listen_mode = False
            if not self.voice.is_speaking and not self._gemini_busy:
                self._update_mic_indicator(False)
            if err and not was_bg:
                self._show_caption(str(err), secs=5.0)
            if not was_bg:
                self._mic_error_streak += 1
                if self._mic_error_streak >= 4:
                    self._backoff_until = time.monotonic() + 18.0
                    self._mic_error_streak = 0
            if not self.voice.is_speaking and self.face.mood != "sleeping":
                self.face.set_mood("neutral")
        except Exception:
            pass

    def _is_hey_tu_trigger(self, text):
        return bool(
            re.match(
                r"^\s*(?:hey|oye)\s*,?\s*t[úu](?:\b|[,:;?!.\-]|$)",
                text,
                flags=re.IGNORECASE,
            )
        )

    def _is_only_hey_tu(self, text):
        return bool(
            re.fullmatch(
                r"\s*(?:hey|oye)\s*,?\s*t[úu]\s*[.!?]?\s*",
                text,
                flags=re.IGNORECASE,
            )
        )

    def _strip_hey_tu_trigger(self, text):
        return re.sub(
            r"^\s*(?:hey|oye)\s*,?\s*t[úu]\s*[,:;\-]?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

    def _has_agrio_trigger(self, text):
        return bool(
            re.match(
                r"^\s*(?:hey|oye)?\s*,?\s*(?:agrio|ágrio|agrío|agro|ario|audio)(?:\b|[,:;?!.\-]|$)",
                text,
                flags=re.IGNORECASE,
            )
        )

    def _strip_agrio_trigger(self, text):
        return re.sub(
            r"^\s*(?:hey|oye)?\s*,?\s*(?:agrio|ágrio|agrío|agro|ario|audio)\b\s*[,:;\-]?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

    def _on_heard_speech(self, heard_text, was_bg=False):
        try:
            self._mic_error_streak = 0
            was_manual = self._manual_listen_mode
            self._manual_listen_mode = False
            self._update_mic_indicator(False)

            clean = (heard_text or "").strip()
            if not clean:
                return

            self._show_caption(f"Tú: {clean}", secs=3.5)

            if self.listener.mode == "android":
                self.handle_command(clean, require_wake=False)
                return

            if self._is_only_hey_tu(clean):
                secs = int(self._get_listen_seconds())
                self._show_caption(f"Te escucho ({secs}s)...", secs=2.5)
                self.face.set_mood("listening")
                Clock.schedule_once(lambda *_: self.handle_mic_badge_touch(), 0.25)
                return

            if self._is_hey_tu_trigger(clean):
                cmd_body = self._strip_hey_tu_trigger(clean) or clean
                self.handle_command(cmd_body, require_wake=False)
                return

            if was_manual or not was_bg:
                self.handle_command(clean, require_wake=False)
                return

            if self._has_agrio_trigger(clean):
                self.handle_command(clean, require_wake=True)
        except Exception as exc:
            log_error("HEARD_SPEECH", exc)
            self._say_and_show(
                "Escuché algo pero hubo un detalle al responder", mood="neutral", show_secs=4.0
            )

    def _try_local_math(self, text):
        try:
            if not text:
                return None

            cleaned = text.lower().strip()
            cleaned = re.sub(
                r"^(?:¿?\s*(?:cu[aá]nto\s+es|calcula|resuelve|dime\s+cu[aá]nto\s+es|a\s+cu[aá]nto\s+equivale)\s+)",
                "",
                cleaned,
            )
            cleaned = cleaned.rstrip("?.! ")

            replacements = [
                (r"\bra[ií]z\s+cuadrada\s+de\s+(\d+(?:\.\d+)?)", r"math.sqrt(\1)"),
                (r"\bra[ií]z\s+de\s+(\d+(?:\.\d+)?)", r"math.sqrt(\1)"),
                (r"\bal\s+cuadrado\b", "**2"),
                (r"\bal\s+cubo\b", "**3"),
                (r"\belevado\s+a\s+(?:la\s+)?", "**"),
                (r"\bm[aá]s\b", "+"),
                (r"\bmenos\b", "-"),
                (r"\bmultiplicado\s+por\b", "*"),
                (r"\bpor\b", "*"),
                (r"\bdividido\s+(?:entre|por)\b", "/"),
                (r"\bentre\b", "/"),
                (r"\bmodulo\b|\bm[oó]dulo\b", "%"),
                (r"(?<=\d)\s*[x×]\s*(?=\d)", "*"),
                (r"÷", "/"),
                (r"\^", "**"),
            ]
            expr = cleaned
            for pat, rep in replacements:
                expr = re.sub(pat, rep, expr)

            def _sqrt_repl(m):
                val = float(m.group(1))
                if val < 0:
                    raise ValueError("Raíz negativa")
                return str(math.sqrt(val))

            expr = re.sub(r"math\.sqrt\((\d+(?:\.\d+)?)\)", _sqrt_repl, expr)
            expr = expr.replace(",", ".")

            if not re.fullmatch(r"[\d\s\+\-\*\/\%\(\)\.]+", expr):
                return None
            if not re.search(r"[\+\-\*\/\%]", expr):
                return None

            if re.search(r"[\+\-\*\/\%]\s*$", expr):
                return "Se cortó la operación, dilo completo"

            ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Mod: operator.mod,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
                ast.UAdd: operator.pos,
            }

            def _eval_node(node):
                if isinstance(node, ast.Expression):
                    return _eval_node(node.body)
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                    return node.value
                if isinstance(node, ast.BinOp) and type(node.op) in ops:
                    left = _eval_node(node.left)
                    right = _eval_node(node.right)
                    if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                        raise ValueError("Exponente muy grande")
                    return ops[type(node.op)](left, right)
                if isinstance(node, ast.UnaryOp) and type(node.op) in ops:
                    return ops[type(node.op)](_eval_node(node.operand))
                raise ValueError("Operación no soportada")

            tree = ast.parse(expr, mode="eval")
            res = _eval_node(tree)
            if isinstance(res, float):
                if res.is_integer():
                    formatted = str(int(res))
                else:
                    formatted = f"{res:.4f}".rstrip("0").rstrip(".").replace(".", " punto ")
            else:
                formatted = str(res)
            return f"El resultado es {formatted}"
        except ZeroDivisionError:
            return "No se puede dividir entre cero"
        except Exception:
            return None

    def handle_face_touch(self, pos):
        try:
            now = time.monotonic()
            if now - self._last_tap_ts < 1.1:
                self._rapid_taps += 1
            else:
                self._rapid_taps = 1
            self._last_tap_ts = now

            if self._rapid_taps >= 3:
                phrase, mood = "¡Hey, despacio! ¡No molestes tanto!", "annoyed"
            else:
                phrase, mood = TOUCH_PHRASES[self._touch_index % len(TOUCH_PHRASES)]
                self._touch_index += 1

            self._say_and_show(phrase, mood=mood, show_secs=3.5)

            if (
                mood != "annoyed"
                and self.listener.mode == "pc_mic"
                and self.listener.available
                and not self.listener._waiting_result
            ):
                Clock.schedule_once(lambda *_: self.handle_mic_badge_touch(), 1.2)
        except Exception as exc:
            log_error("HANDLE_FACE_TOUCH", exc)

    def _update_timer_badge(self):
        try:
            if self.remaining_sec > 0:
                mins = self.remaining_sec // 60
                secs = self.remaining_sec % 60
                self.timer_badge.text = f"Pomodoro {mins:02d}:{secs:02d}"
            else:
                self.timer_badge.text = "Menú"
        except Exception:
            pass

    def start_timer(self, seconds, label="Pomodoro"):
        try:
            if self._timer_ev:
                self._timer_ev.cancel()
            self.initial_sec = int(seconds)
            self.remaining_sec = int(seconds)
            self._update_timer_badge()
            self.face.set_mood("focused")
            self._say_and_show(
                f"{label} iniciado: {int(seconds) // 60} minutos", mood="focused", show_secs=4.5
            )
            self._timer_ev = Clock.schedule_interval(self._tick_timer, 1.0)
        except Exception as exc:
            log_error("START_TIMER", exc)

    def stop_timer(self):
        try:
            if self._timer_ev:
                self._timer_ev.cancel()
                self._timer_ev = None
            self.remaining_sec = 0
            self._update_timer_badge()
            self._say_and_show("Temporizador detenido", mood="neutral", show_secs=4.0)
        except Exception as exc:
            log_error("STOP_TIMER", exc)

    def reset_timer(self):
        try:
            if self._timer_ev:
                self._timer_ev.cancel()
                self._timer_ev = None
            self.remaining_sec = self.initial_sec if self.initial_sec > 0 else POMODORO_SECONDS
            self._update_timer_badge()
            self._say_and_show("Temporizador reiniciado", mood="neutral", show_secs=4.0)
        except Exception as exc:
            log_error("RESET_TIMER", exc)

    def _tick_timer(self, dt):
        try:
            if self.remaining_sec > 0:
                self.remaining_sec -= 1
                self._update_timer_badge()
                if self.remaining_sec in (5 * 60, 60):
                    mins = self.remaining_sec // 60
                    self._say_and_show(
                        f"Queda {mins} minuto" + ("s" if mins != 1 else ""),
                        mood="speaking",
                        show_secs=4.0,
                    )
            else:
                if self._timer_ev:
                    self._timer_ev.cancel()
                    self._timer_ev = None
                self._update_timer_badge()
                self._say_and_show("¡Tiempo terminado!", mood="surprised", show_secs=4.5)
        except Exception as exc:
            log_error("TICK_TIMER", exc)

    def _add_reminder(self, minutes_delay, note_text):
        try:
            due_ts = time.time() + max(1, int(minutes_delay)) * 60
            reminders = self.store.data.get("reminders") or []
            reminders.append({"due_ts": due_ts, "text": note_text.strip()})
            self.store.data["reminders"] = reminders
            self.store.save()
        except Exception as exc:
            log_error("ADD_REMINDER", exc)

    def _check_reminders_tick(self, dt):
        try:
            reminders = list(self.store.data.get("reminders") or [])
            if not reminders:
                return
            now_ts = time.time()
            pending = []
            triggered = []
            for item in reminders:
                if float(item.get("due_ts", 0)) <= now_ts:
                    triggered.append(str(item.get("text") or "Recordatorio"))
                else:
                    pending.append(item)
            if triggered:
                self.store.data["reminders"] = pending
                self.store.save()
                for msg in triggered:
                    aviso = f"Recordatorio: {msg}"
                    self._say_and_show(aviso, mood="surprised", show_secs=5.0)
                    self._run_telegram_voice(aviso, silent_ok=True)
        except Exception as exc:
            log_error("REMINDERS", exc)

    def change_volume(self, delta):
        try:
            vol = max(10, min(100, int(self.store.data.get("volume", 90)) + delta))
            self.store.data["volume"] = vol
            self.store.save()
            self._say_and_show(f"Volumen al {vol} por ciento", mood="speaking", show_secs=4.0)
        except Exception as exc:
            log_error("CHANGE_VOL", exc)

    def _append_history(self, user_msg, ai_msg):
        try:
            self._chat_history.append(("user", user_msg))
            self._chat_history.append(("model", ai_msg))
            self._last_ai_reply = ai_msg
            if len(self._chat_history) > 8:
                self._chat_history = self._chat_history[-8:]
        except Exception:
            pass

    def handle_command(self, raw, require_wake=False):
        try:
            text = (raw or "").strip()
            if not text:
                return

            used_agrio = self._has_agrio_trigger(text)
            if require_wake and not used_agrio:
                return

            if re.fullmatch(
                r"\s*(?:hey|oye)?\s*,?\s*(?:agrio|ágrio|agrío|agro|ario|audio)\s*[.!?]?\s*",
                text,
                flags=re.IGNORECASE,
            ):
                self._say_and_show(random.choice(GREETINGS), mood="happy", show_secs=4.5)
                return

            stripped = self._strip_agrio_trigger(text)
            effective = stripped if stripped else text
            low = effective.lower()
            n_words = len(low.split())

            if any(k in low for k in ("despierta", "despertar")):
                self.face.set_mood("surprised")
                self._say_and_show("¡Despierto y listo!", mood="surprised", show_secs=4.5)
                return

            if n_words <= 5 and any(
                k in low for k in ("a dormir", "duerme", "dormir", "a descansar", "reposo")
            ):
                self._say_and_show(
                    "A dormir, avísame cuando me necesites", mood="sleeping", show_secs=4.5
                )
                self.face.set_mood("sleeping")
                return

            if n_words <= 4 and any(
                k in low for k in ("adiós", "adios", "nos vemos", "hasta luego", "chao")
            ):
                self._say_and_show("¡Nos vemos! Aquí sigo", mood="sleeping", show_secs=4.5)
                self.face.set_mood("sleeping")
                return

            if n_words <= 4 and any(
                k in low
                for k in (
                    "hola",
                    "buenos días",
                    "buenos dias",
                    "buenas tardes",
                    "buenas noches",
                    "qué onda",
                    "que onda",
                )
            ):
                self._say_and_show(random.choice(GREETINGS), mood="happy", show_secs=4.5)
                return

            if any(
                k in low
                for k in (
                    "cómo estás",
                    "como estas",
                    "qué tal",
                    "que tal",
                    "cómo andas",
                    "como andas",
                )
            ):
                self._say_and_show(random.choice(HOW_ARE_YOU), mood="happy", show_secs=4.5)
                return

            if any(
                k in low
                for k in (
                    "quién eres",
                    "quien eres",
                    "qué haces",
                    "que haces",
                    "para qué sirves",
                    "para que sirves",
                )
            ):
                self._say_and_show(
                    "Soy Agrio, tu asistente con hora, fecha, pomodoro, recordatorios, telegram y Gemini.",
                    mood="speaking",
                    show_secs=5.0,
                )
                return

            if re.search(r"\b(?:qué hora|que hora|dame la hora|la hora)\b", low) or low == "hora":
                now = datetime.datetime.now()
                hora_txt = (
                    f"Son las {now.strftime('%I:%M %p')}"
                    .replace("AM", "de la mañana")
                    .replace("PM", "de la tarde")
                )
                self._say_and_show(hora_txt, mood="speaking", show_secs=4.5)
                return

            if re.search(
                r"\b(?:qué día|que dia|qué fecha|que fecha|hoy es|la fecha)\b", low
            ) or low == "fecha":
                now = datetime.datetime.now()
                fecha_txt = (
                    f"Hoy es {DIAS_ES[now.weekday()]} {now.day} de {MESES_ES[now.month - 1]} de {now.year}"
                )
                self._say_and_show(fecha_txt, mood="speaking", show_secs=5.0)
                return

            rem_match = re.search(
                r"(?:puedes\s+|me\s+|por\s+favor\s+)?(?:recuérdame|recuerdame|recordatorio)\s+(?:en\s+)?(\d+|un|una)\s*(?:min|minutos?|hora|horas?)\s*(?:que\s+|de\s+|para\s+)?(.+)",
                effective,
                flags=re.IGNORECASE,
            )
            if rem_match:
                raw_num = rem_match.group(1).lower()
                mins_val = 1 if raw_num in ("un", "una") else int(raw_num)
                if re.search(r"\bhoras?\b", effective, flags=re.IGNORECASE):
                    mins_val *= 60
                nota_val = rem_match.group(2).strip()
                self._add_reminder(mins_val, nota_val)
                self._say_and_show(
                    f"Listo, te recuerdo en {mins_val} minuto{'s' if mins_val != 1 else ''}: {nota_val}",
                    mood="happy",
                    show_secs=4.5,
                )
                return

            if "pomodoro" in low or "concentr" in low:
                self.start_timer(POMODORO_SECONDS, "Pomodoro")
                return

            if n_words <= 4 and any(k in low for k in ("reinicia", "reiniciar", "reset")):
                self.reset_timer()
                return

            if n_words <= 4 and re.search(r"\b(?:deten|detener|para|parar|stop)\b", low):
                self.stop_timer()
                return

            if any(
                k in low for k in ("sube el volumen", "sube volumen", "más volumen", "mas volumen")
            ):
                self.change_volume(15)
                return

            if any(k in low for k in ("baja el volumen", "baja volumen", "menos volumen")):
                self.change_volume(-15)
                return

            if any(k in low for k in ("chiste", "cuéntame algo", "cuentame algo", "broma")):
                self._say_and_show(random.choice(JOKES), mood="happy", show_secs=5.0)
                return

            if any(
                k in low
                for k in ("motivación", "motivacion", "ánimos", "animos", "motívame", "motivame")
            ):
                self._say_and_show(random.choice(MOTIVATION), mood="happy", show_secs=4.5)
                return

            if low.startswith("buscar ") or low.startswith("tavily "):
                q = effective.split(" ", 1)[1].strip()
                self._run_tavily_voice(q)
                return

            if (
                "última respuesta" in low
                or "ultima respuesta" in low
                or "lo último" in low
                or "lo ultimo" in low
            ) and ("telegram" in low or "tg" in low):
                if self._last_ai_reply:
                    self._run_telegram_voice(self._last_ai_reply)
                else:
                    self._say_and_show(
                        "Aún no tengo una respuesta guardada para enviar",
                        mood="neutral",
                        show_secs=4.5,
                    )
                return

            if low.startswith("telegram ") or low.startswith("tg "):
                msg = effective.split(" ", 1)[1].strip()
                self._run_telegram_voice(msg)
                return

            math_reply = self._try_local_math(effective)
            if math_reply:
                self._say_and_show(math_reply, mood="speaking", show_secs=4.5)
                return

            if used_agrio:
                self._run_gemini_voice(effective)
            else:
                self._say_and_show(
                    "No conozco ese comando. Para preguntarle a Gemini di 'Hey Agrio' y tu pregunta",
                    mood="neutral",
                    show_secs=5.5,
                )
        except Exception as exc:
            log_error("HANDLE_CMD", exc)
            self._say_and_show(
                "Tuve un detalle al procesar el comando", mood="neutral", show_secs=4.5
            )

    def _run_gemini_voice(self, prompt):
        try:
            api_key = "".join(str(self._get_gemini_key()).split())

            if not api_key:
                self._say_and_show(
                    "Configura tu Gemini API Key en el botón Menú", mood="neutral", show_secs=4.5
                )
                return

            if self._gemini_busy:
                self._say_and_show(
                    "Un momento, sigo pensando la anterior", mood="thinking", show_secs=4.0
                )
                return

            self._gemini_busy = True
            self._update_mic_indicator(False, custom_status="Pensando")
            self._show_caption("Pensando con Gemini...", secs=6.0)
            self.face.set_mood("thinking")

            primary_model = self._get_gemini_model() or DEFAULT_GEMINI_MODEL

            models_to_try = [primary_model]
            for fallback_m in ("gemini-2.5-flash", "gemini-2.0-flash"):
                if fallback_m not in models_to_try:
                    models_to_try.append(fallback_m)

            detailed = str(self.store.data.get("response_style", "Corto")) == "Detallado"
            style_instr = (
                "Responde en español de forma clara y útil en 2 o 3 oraciones breves para leer en voz alta, "
                "sin listas largas ni markdown complejo."
                if detailed
                else "Responde en español en máximo 2 oraciones cortas y directas para leer en voz alta, "
                "sin listas largas ni markdown complejo."
            )
            max_tokens = 240 if detailed else 140

            contents = []
            for role, hist_txt in self._chat_history[-6:]:
                contents.append({"role": role, "parts": [{"text": hist_txt}]})
            contents.append(
                {"role": "user", "parts": [{"text": f"{style_instr}\n\nPregunta: {prompt}"}]}
            )

            def _finish_ai(text_out, mood_out, secs_out, save_turn=False):
                def _apply(*_):
                    self._gemini_busy = False
                    self._update_mic_indicator(False)
                    if save_turn:
                        self._append_history(prompt, text_out)
                    self._say_and_show(text_out, mood=mood_out, show_secs=secs_out)

                Clock.schedule_once(_apply, 0)

            def _worker():
                try:
                    payload = json.dumps(
                        {
                            "contents": contents,
                            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7},
                        }
                    ).encode("utf-8")

                    last_code = None
                    for model_name in models_to_try:
                        url = (
                            f"https://generativelanguage.googleapis.com/v1beta/models/"
                            f"{model_name}:generateContent?key={urllib.parse.quote(api_key)}"
                        )
                        for attempt in range(2):
                            try:
                                req = urllib.request.Request(
                                    url,
                                    data=payload,
                                    headers={"Content-Type": "application/json"},
                                    method="POST",
                                )
                                with _urlopen_with_ssl_fallback(req, timeout=16) as resp:
                                    parsed = json.loads(resp.read().decode("utf-8"))

                                reply = ""
                                for cand in parsed.get("candidates") or []:
                                    parts = (cand.get("content") or {}).get("parts") or []
                                    for pt in parts:
                                        if isinstance(pt, dict) and pt.get("text"):
                                            reply += str(pt["text"])
                                reply = re.sub(r"\s+", " ", reply).strip()

                                if not reply:
                                    reply = "No recibí respuesta de Gemini."
                                    _finish_ai(reply, "neutral", 4.5, save_turn=False)
                                    return

                                limit_chars = 360 if detailed else 220
                                _finish_ai(
                                    reply[:limit_chars],
                                    "speaking",
                                    6.0 if detailed else 5.2,
                                    save_turn=True,
                                )
                                return
                            except urllib.error.HTTPError as he:
                                last_code = he.code
                                err_body = ""
                                try:
                                    err_body = he.read().decode("utf-8", errors="replace")
                                except Exception:
                                    pass
                                log_error("GEMINI_HTTP", f"{model_name} HTTP {he.code}: {err_body}")
                                if he.code in (503, 429) and attempt == 0:
                                    time.sleep(1.3)
                                    continue
                                break
                            except Exception as exc:
                                log_error("GEMINI_EXC", exc)
                                short_err = str(exc).strip()[:45] or "error de red"
                                _finish_ai(
                                    f"Error Gemini ({short_err})", "annoyed", 4.5, save_turn=False
                                )
                                return

                    if last_code == 503:
                        _finish_ai(
                            "Gemini está saturado ahorita, intenta de nuevo en un momento",
                            "neutral",
                            4.5,
                            save_turn=False,
                        )
                    else:
                        _finish_ai(
                            f"Gemini HTTP {last_code if last_code else 503}",
                            "annoyed",
                            4.5,
                            save_turn=False,
                        )
                except Exception as exc:
                    log_error("GEMINI_WORKER", exc)
                    _finish_ai("Error interno en Gemini", "annoyed", 4.5, save_turn=False)

            threading.Thread(target=_worker, daemon=True).start()
        except Exception as exc:
            log_error("GEMINI_THREAD", exc)
            self._gemini_busy = False
            self._update_mic_indicator(False)
            self._say_and_show(
                "No pude iniciar la consulta a Gemini", mood="annoyed", show_secs=4.5
            )

    def _run_tavily_voice(self, query):
        try:
            key = os.environ.get("XIAOZHI_TAVILY_API_KEY", "").strip()
            if not key:
                self._say_and_show(
                    "No tengo configurada la clave de Tavily", mood="neutral", show_secs=4.5
                )
                return
            self._show_caption(f"Buscando {query}...", secs=5.0)

            def _worker():
                try:
                    payload = json.dumps(
                        {"api_key": key, "query": query, "max_results": 1}
                    ).encode("utf-8")
                    req = urllib.request.Request(
                        "https://api.tavily.com/search",
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with _urlopen_with_ssl_fallback(req, timeout=12) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                    results = data.get("results") or []
                    spoken = (
                        results[0].get("content", "Sin resultados")[:200]
                        if results
                        else "No encontré nada"
                    )
                    self._last_ai_reply = spoken
                    Clock.schedule_once(
                        lambda *_: self._say_and_show(spoken, mood="speaking", show_secs=5.5), 0
                    )
                except Exception as exc:
                    log_error("TAVILY", exc)
                    Clock.schedule_once(
                        lambda *_: self._say_and_show(
                            "Hubo un error buscando en internet", mood="neutral", show_secs=4.5
                        ),
                        0,
                    )

            threading.Thread(target=_worker, daemon=True).start()
        except Exception as exc:
            log_error("TAVILY_START", exc)

    def _run_telegram_voice(self, message, silent_ok=False):
        try:
            token = str(
                self.store.data.get("telegram_token")
                or os.environ.get("XIAOZHI_TELEGRAM_BOT_TOKEN")
                or DEFAULT_TELEGRAM_TOKEN
            ).strip()
            chat_id = str(
                self.store.data.get("telegram_chat_id")
                or os.environ.get("XIAOZHI_TELEGRAM_CHAT_ID")
                or DEFAULT_TELEGRAM_CHAT_ID
            ).strip()

            if not token or not chat_id:
                log_error("TELEGRAM_CFG", "Falta token o chat_id de Telegram")
                if not silent_ok:
                    self._say_and_show(
                        "Configura el token y el chat id de Telegram en el Menú",
                        mood="neutral",
                        show_secs=4.5,
                    )
                return

            def _post_telegram():
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                body = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
                req = urllib.request.Request(url, data=body, method="POST")
                with _urlopen_with_ssl_fallback(req, timeout=12) as resp:
                    return json.loads(resp.read().decode("utf-8"))

            def _worker():
                try:
                    parsed = _post_telegram()
                    if parsed.get("ok"):
                        if not silent_ok:
                            Clock.schedule_once(
                                lambda *_: self._say_and_show(
                                    "Mensaje enviado por Telegram", mood="speaking", show_secs=4.5
                                ),
                                0,
                            )
                    else:
                        desc = str(parsed.get("description") or "Error de Telegram")
                        log_error("TELEGRAM_API", desc)
                        if not silent_ok:
                            Clock.schedule_once(
                                lambda *_: self._say_and_show(
                                    f"Telegram: {desc[:65]}", mood="annoyed", show_secs=4.5
                                ),
                                0,
                            )
                except urllib.error.HTTPError as he:
                    err_txt = ""
                    try:
                        err_txt = he.read().decode("utf-8", errors="replace")[:160]
                    except Exception:
                        pass
                    log_error("TELEGRAM_HTTP", f"HTTP {he.code}: {err_txt}")
                    if not silent_ok:
                        Clock.schedule_once(
                            lambda *_, code=he.code: self._say_and_show(
                                f"Telegram HTTP {code}", mood="annoyed", show_secs=4.5
                            ),
                            0,
                        )
                except Exception as exc:
                    log_error("TELEGRAM_EXC", exc)
                    short_err = str(exc).strip()[:45] or "sin red"
                    if not silent_ok:
                        Clock.schedule_once(
                            lambda *_, err=short_err: self._say_and_show(
                                f"Sin conexión con Telegram ({err})", mood="annoyed", show_secs=4.5
                            ),
                            0,
                        )

            threading.Thread(target=_worker, daemon=True).start()
        except Exception as exc:
            log_error("TELEGRAM_START", exc)


class AgrioApp(App):
    def build(self):
        try:
            load_env_file()
            _cleanup_old_temp_audio(120)
            self.title = "Agrio"
            store = AgrioStore()
            self.root_widget = AgrioFaceOnlyRoot(store)
            if KEEP_SCREEN_ON:
                Clock.schedule_once(lambda *_: set_keep_screen_on(True), 0.5)
                Clock.schedule_once(lambda *_: set_keep_screen_on(True), 3.0)
            return self.root_widget
        except Exception as exc:
            log_error("APP_BUILD", exc)
            return Label(text=f"Error al iniciar Agrio: {exc}")

    def on_stop(self):
        try:
            if KEEP_SCREEN_ON:
                set_keep_screen_on(False)
        except Exception as exc:
            log_error("APP_STOP", exc)

    def on_resume(self):
        try:
            if KEEP_SCREEN_ON:
                set_keep_screen_on(True)
            root = getattr(self, "root_widget", None)
            if root and hasattr(root, "listener"):
                if not root.voice.is_speaking and not root._gemini_busy:
                    root._update_mic_indicator(False)
        except Exception as exc:
            log_error("APP_RESUME", exc)
        return True


if __name__ == "__main__":
    try:
        AgrioApp().run()
    except Exception as exc:
        log_error("APP_FATAL", exc)
