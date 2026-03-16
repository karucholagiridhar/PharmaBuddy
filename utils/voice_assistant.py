"""
Voice Assistant Module
Speech-to-text and text-to-speech capabilities
"""
import streamlit as st
from gtts import gTTS
import speech_recognition as sr
from io import BytesIO
import tempfile
import os
from utils.utils import setup_logger

logger = setup_logger(__name__)


class VoiceAssistant:
    """Voice interaction capabilities"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.supported_languages = {
            "en": "en-US",
            "hi": "hi-IN",
            "ta": "ta-IN",
            "te": "te-IN",
            "bn": "bn-IN",
            "mr": "mr-IN",
            "gu": "gu-IN",
            "kn": "kn-IN",
            "ml": "ml-IN",
            "pa": "pa-IN"
        }
    
    def get_speech_language(self, app_language: str) -> str:
        """Convert app language code to speech recognition language"""
        return self.supported_languages.get(app_language, "en-US")
    
    def text_to_speech(self, text: str, language: str = "en") -> BytesIO:
        """
        Convert text to speech audio
        Returns audio bytes that can be played
        """
        try:
            # Create speech
            tts = gTTS(text=text, lang=language, slow=False)
            
            # Save to bytes
            audio_bytes = BytesIO()
            tts.write_to_fp(audio_bytes)
            audio_bytes.seek(0)
            
            logger.info("Text-to-speech conversion successful")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Text-to-speech error: {str(e)}")
            return None
    
    def speech_to_text(self, audio_data, language: str = "en-US") -> str:
        """
        Convert speech to text
        """
        try:
            # Use Google Speech Recognition
            text = self.recognizer.recognize_google(audio_data, language=language)
            logger.info(f"Speech recognized: {text}")
            return text
            
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Speech recognition error: {str(e)}")
            return None
    
    def listen_from_microphone(self, language: str = "en-US", timeout: int = 5) -> str:
        """
        Listen to microphone and convert to text
        """
        try:
            # Check if PyAudio is available (required for Microphone)
            try:
                import pyaudio
            except ImportError:
                logger.warning("PyAudio not installed - Microphone input disabled")
                st.error("🎤 Microphone input is not available in this environment (Server-side audio not supported)")
                return None

            with sr.Microphone() as source:
                logger.info("Listening...")
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                # Listen
                audio = self.recognizer.listen(source, timeout=timeout)
                # Convert to text
                return self.speech_to_text(audio, language)
                
        except Exception as e:
            logger.error(f"Microphone error: {str(e)}")
            return None


def render_voice_input_button(key: str = "voice_input") -> str:
    """
    Render a voice input button that returns transcribed text
    Returns the transcribed text or None
    """
    col1, col2 = st.columns([5, 1])
    
    with col2:
        if st.button("🎤", key=key, help="Click to speak (Local only)", use_container_width=True):
            st.session_state[f"{key}_listening"] = True
    
    # If listening state is active
    if st.session_state.get(f"{key}_listening", False):
        with st.spinner("🎤 Listening..."):
            voice_assistant = st.session_state.get('voice_assistant')
            if not voice_assistant:
                voice_assistant = VoiceAssistant()
                st.session_state.voice_assistant = voice_assistant
            
            # Get current language
            current_lang = st.session_state.get('user_language', 'en')
            speech_lang = voice_assistant.get_speech_language(current_lang)
            
            # Listen
            text = voice_assistant.listen_from_microphone(language=speech_lang)
            
            # Reset listening state
            st.session_state[f"{key}_listening"] = False
            
            if text:
                st.success(f"✓ Heard: {text}")
                return text
            elif text is None:
                # If None was returned, error was likely already shown (e.g. missing PyAudio)
                pass
            else:
                st.error("❌ Could not understand. Please try again.")
                return None
    
    return None


def render_voice_output_button(text: str, language: str = "en", key: str = "voice_output"):
    """
    Render a button that reads text aloud
    """
    if st.button("🔊 Read Aloud", key=key, help="Click to hear this response"):
        try:
            voice_assistant = st.session_state.get('voice_assistant')
            if not voice_assistant:
                voice_assistant = VoiceAssistant()
                st.session_state.voice_assistant = voice_assistant
            
            with st.spinner("🔊 Generating audio..."):
                audio_bytes = voice_assistant.text_to_speech(text, language)
                
                if audio_bytes:
                    st.audio(audio_bytes, format='audio/mp3')
                else:
                    st.error("Could not generate audio")
                    
        except Exception as e:
            st.error(f"Audio generation failed: {str(e)}")
            logger.error(f"Voice output error: {str(e)}")
