/**
 * frontend/src/i18n.js
 * Initialises react-i18next with English and Kannada catalogues.
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import kn from "./locales/kn.json";

const savedLng = localStorage.getItem("vl_lang") || "en";

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    kn: { translation: kn },
  },
  lng: savedLng,
  fallbackLng: "en",
  interpolation: {
    escapeValue: false, // React already escapes values
  },
});

export default i18n;
