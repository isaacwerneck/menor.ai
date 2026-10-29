"""Interface de voz opcional que usa o mesmo fluxo de inferência do assistant.py."""
from pathlib import Path
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None
try:
    import speech_recognition as sr
except ImportError:
    sr = None


class VoiceEngine:
    def __init__(self):
        self.tts = None
        if pyttsx3:
            try:
                self.tts = pyttsx3.init()
            except Exception:
                pass
        self.recognizer = sr.Recognizer() if sr else None

    def falar(self, texto: str) -> None:
        print(f"\nMenor (voz): {texto}")
        if self.tts:
            try:
                self.tts.say(texto)
                self.tts.runAndWait()
            except Exception as exc:
                print(f"[TTS indisponível: {exc}]")

    def escutar(self, timeout: int = 7) -> str:
        if not self.recognizer:
            return input("Você (voz simulada, texto): ").strip()
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = self.recognizer.listen(source, timeout=timeout)
            if hasattr(self.recognizer, "recognize_whisper"):
                return self.recognizer.recognize_whisper(audio, language="portuguese")
            return self.recognizer.recognize_google(audio, language="pt-BR")
        except Exception as exc:
            print(f"[Reconhecimento falhou: {exc}]")
            return input("Você (texto): ").strip()


def make_voice_confirm(voice: VoiceEngine):
    from assistant import confirmation

    def _voice_confirm(action: str, target: str, preview: str = "") -> bool:
        voice.falar(f"Atenção: permissão necessária no terminal para {action} em {Path(target).name}.")
        return confirmation(action, target, preview)

    return _voice_confirm


def executar_assistente_voz():
    from assistant import respond, build_system_message

    voice = VoiceEngine()
    history = [build_system_message()]
    confirm_cb = make_voice_confirm(voice)
    voice.falar("Menor ativado. Pode falar.")
    while True:
        try:
            text = voice.escutar()
        except (EOFError, KeyboardInterrupt):
            voice.falar("Até mais!")
            break
        if text.casefold() in {"sair", "encerrar", "desligar", "quit"}:
            voice.falar("Até mais!")
            break
        if not text:
            continue
        answer = respond(text, history, stream_text=False, confirm_fn=confirm_cb)
        voice.falar(answer)


if __name__ == "__main__":
    executar_assistente_voz()
