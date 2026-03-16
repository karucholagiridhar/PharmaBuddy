"""
Multi-language Translation Support
Supports Hindi and other regional Indian languages
"""
from typing import Dict, Optional
from deep_translator import GoogleTranslator
from utils.utils import setup_logger

logger = setup_logger(__name__)


class LanguageManager:
    """Manages multi-language translation"""
    
    # Supported languages
    LANGUAGES = {
        "en": "English",
        "hi": "Hindi (हिंदी)",
        "ta": "Tamil (தமிழ்)",
        "te": "Telugu (తెలుగు)",
        "bn": "Bengali (বাংলা)",
        "mr": "Marathi (मराठी)",
        "gu": "Gujarati (ગુજરાતી)",
        "kn": "Kannada (ಕನ್ನಡ)",
        "ml": "Malayalam (മലയാളം)",
        "pa": "Punjabi (ਪੰਜਾਬੀ)"
    }
    
    # Common UI translations (preloaded for speed)
    UI_TRANSLATIONS = {
        "en": {
            "welcome": "Welcome to Medi-Mate",
            "login": "Login",
            "register": "Register",
            "logout": "Logout",
            "upload_prescription": "Upload Prescription",
            "ask_question": "Ask a question about your prescription",
            "medicine_reminder": "Medicine Reminders",
            "pharmacy_locator": "Find Pharmacy",
            "otc_checker": "OTC Medicine Checker",
            "chat_history": "Chat History",
            "prescription_history": "Prescription History",
            "add_reminder": "Add Reminder",
            "medicine_name": "Medicine Name",
            "dosage": "Dosage",
            "frequency": "Frequency",
            "time": "Time",
            "duration": "Duration (days)",
            "save": "Save",
            "cancel": "Cancel",
            "delete": "Delete",
            "mark_taken": "Mark as Taken",
            "search": "Search",
            "phone": "Phone",
            "address": "Address",
            "rating": "Rating",
            "open_now": "Open Now",
            "closed": "Closed",
            "get_directions": "Get Directions",
            "safe_to_buy": "Safe to Buy",
            "consult_doctor": "Consult Doctor",
            "settings": "Settings",
            "language": "Language",
            "daily": "Daily",
            "twice_daily": "Twice Daily",
            "thrice_daily": "Three Times Daily",
            "weekly": "Weekly",
            "with_food": "With Food",
            "before_food": "Before Food",
            "after_food": "After Food",
            "my_prescriptions": "My Prescriptions",
            "my_medications": "My Medications",
            "find_pharmacy": "Find Pharmacy",
            "drug_info": "Drug Information",
            "menu": "Menu",
            "current_medications": "Current Medications",
            "add_medication": "Add Medication",
            "my_progress": "My Progress",
            "todays_schedule": "Today's Schedule",
            "log_dose": "Log Dose",
            "select_medication": "Select Medication",
            "time_slot": "Time Slot",
            "status": "Status",
            "notes_optional": "Notes (Optional)",
            "save_schedule": "Save Medication Schedule",
            "gps_location": "GPS Location",
            "address_search": "Address Search"
        },
        "hi": {
            "welcome": "मेडी-मेट में आपका स्वागत है",
            "login": "लॉग इन करें",
            "register": "पंजीकरण करें",
            "logout": "लॉग आउट",
            "upload_prescription": "प्रिस्क्रिप्शन अपलोड करें",
            "ask_question": "अपनी दवा के बारे में पूछें",
            "medicine_reminder": "दवा अनुस्मारक",
            "pharmacy_locator": "फार्मेसी खोजें",
            "otc_checker": "ओटीसी दवा जांचकर्ता",
            "chat_history": "चैट इतिहास",
            "prescription_history": "प्रिस्क्रिप्शन इतिहास",
            "add_reminder": "रिमाइंडर जोड़ें",
            "medicine_name": "दवा का नाम",
            "dosage": "खुराक",
            "frequency": "आवृत्ति",
            "time": "समय",
            "duration": "अवधि (दिन)",
            "save": "सहेजें",
            "cancel": "रद्द करें",
            "delete": "हटाएं",
            "mark_taken": "ली गई के रूप में चिह्नित करें",
            "search": "खोजें",
            "phone": "फोन",
            "address": "पता",
            "rating": "रेटिंग",
            "open_now": "अभी खुला है",
            "closed": "बंद",
            "get_directions": "दिशा-निर्देश प्राप्त करें",
            "safe_to_buy": "खरीदने के लिए सुरक्षित",
            "consult_doctor": "डॉक्टर से परामर्श करें",
            "settings": "सेटिंग्स",
            "language": "भाषा",
            "daily": "दैनिक",
            "twice_daily": "दिन में दो बार",
            "thrice_daily": "दिन में तीन बार",
            "weekly": "साप्ताहिक",
            "with_food": "भोजन के साथ",
            "before_food": "भोजन से पहले",
            "after_food": "भोजन के बाद",
            "my_prescriptions": "मेरे नुस्खे",
            "my_medications": "मेरी दवाइयां",
            "find_pharmacy": "फार्मेसी ढूंढें",
            "drug_info": "दवा जानकारी",
            "menu": "मेन्यू"
        }
    }
    
    def __init__(self):
        self.current_language = "en"
    
    def set_language(self, language_code: str):
        """Set the current language"""
        if language_code in self.LANGUAGES:
            self.current_language = language_code
            logger.info(f"Language set to: {self.LANGUAGES[language_code]}")
        else:
            logger.warning(f"Unsupported language code: {language_code}")
    
    def get_text(self, key: str, language: Optional[str] = None) -> str:
        """
        Get translated text for a UI element
        """
        lang = language or self.current_language
        
        # Return from preloaded translations if available
        if lang in self.UI_TRANSLATIONS and key in self.UI_TRANSLATIONS[lang]:
            return self.UI_TRANSLATIONS[lang][key]
        
        # Fallback to English
        if key in self.UI_TRANSLATIONS["en"]:
            # If target language isn't English, try to translate the English value on the fly
            # This is a fallback-fallback, usually we just return English
            return self.UI_TRANSLATIONS["en"][key]
        
        return key
    
    def translate(self, text: str, target_language: Optional[str] = None, source_language: str = "auto") -> str:
        """
        Translate text using deep_translator
        """
        try:
            target = target_language or self.current_language
            
            # Don't translate if target is English and text is ASCII (likely English) 
            # or if explicitly source=en and target=en
            if target == "en" and source_language == "en":
                return text
                
            translator = GoogleTranslator(source=source_language, target=target)
            return translator.translate(text)
        
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return text  # Return original text if translation fails
    
    def detect_language(self, text: str) -> str:
        """Detect language of given text"""
        # deep_translator doesn't have a robust detect method exposed directly in the same way 
        # as googletrans. We'll default to 'en' or use a simple heuristic if needed.
        # For this app, we mostly rely on explicit language setting.
        return "en"
    
    def translate_prescription_data(self, prescription: Dict, target_language: str) -> Dict:
        """
        Translate prescription data fields
        """
        if target_language == "en":
            return prescription
        
        try:
            translated = prescription.copy()
            
            # Fields to translate
            translatable_fields = [
                "doctor_name",
                "patient_name",
                "diagnosis",
                "instructions",
                "notes"
            ]
            
            for field in translatable_fields:
                if field in prescription and prescription[field]:
                    translated[field] = self.translate(prescription[field], target_language)
            
            # Translate medicines
            if "medicines" in prescription:
                translated["medicines"] = []
                for medicine in prescription["medicines"]:
                    translated_med = medicine.copy()
                    if "instructions" in medicine:
                        translated_med["instructions"] = self.translate(medicine["instructions"], target_language)
                    translated["medicines"].append(translated_med)
            
            return translated
        
        except Exception as e:
            logger.error(f"Error translating prescription: {str(e)}")
            return prescription
    
    def get_language_name(self, code: str) -> str:
        """Get language name from code"""
        return self.LANGUAGES.get(code, "Unknown")
    
    def get_all_languages(self) -> Dict[str, str]:
        """Get all supported languages"""
        return self.LANGUAGES.copy()
