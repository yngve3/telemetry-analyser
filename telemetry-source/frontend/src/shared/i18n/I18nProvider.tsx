import { useQuery } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { getTranslations } from "../api/client";
import type { LanguageResponse, TranslationsResponse } from "../api/types";

type I18nContextValue = {
  language: string;
  languages: LanguageResponse[];
  setLanguage: (language: string) => void;
  t: (key: string, fallback?: string) => string;
  tp: (key: string, count: number, fallback?: string) => string;
};

const DEFAULT_LANGUAGE = "en";
const STORAGE_KEY = "telemetry-source-language";
const fallbackLanguages: LanguageResponse[] = [
  { code: "en", label: "English" },
  { code: "ru", label: "Русский" },
];
const fallbackCatalog: TranslationsResponse = {
  default_language: DEFAULT_LANGUAGE,
  languages: fallbackLanguages,
  messages: {},
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [preferredLanguage, setPreferredLanguage] = useState(() =>
    readStoredLanguage(),
  );
  const translationsQuery = useQuery({
    queryKey: ["translations"],
    queryFn: getTranslations,
    staleTime: Infinity,
    retry: 1,
  });

  const catalog = translationsQuery.data ?? fallbackCatalog;
  const language = catalog.languages.some(
    (item) => item.code === preferredLanguage,
  )
    ? preferredLanguage
    : catalog.default_language;

  const setLanguage = useCallback((nextLanguage: string) => {
    window.localStorage.setItem(STORAGE_KEY, nextLanguage);
    setPreferredLanguage(nextLanguage);
  }, []);

  const t = useCallback(
    (key: string, fallback?: string) =>
      catalog.messages[language]?.[key] ??
      catalog.messages[catalog.default_language]?.[key] ??
      fallback ??
      key,
    [catalog, language],
  );

  const tp = useCallback(
    (key: string, count: number, fallback?: string) => {
      const category = new Intl.PluralRules(language).select(count);
      const messages = catalog.messages[language];
      const defaultMessages = catalog.messages[catalog.default_language];
      const template =
        messages?.[`${key}.${category}`] ??
        messages?.[`${key}.other`] ??
        defaultMessages?.[`${key}.${category}`] ??
        defaultMessages?.[`${key}.other`] ??
        fallback ??
        `${count}`;

      return template.replace(/\{count\}/g, String(count));
    },
    [catalog, language],
  );

  const value = useMemo(
    () => ({
      language,
      languages: catalog.languages,
      setLanguage,
      t,
      tp,
    }),
    [catalog.languages, language, setLanguage, t, tp],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const value = useContext(I18nContext);
  if (value === null) {
    throw new Error("useI18n must be used inside I18nProvider.");
  }
  return value;
}

function readStoredLanguage(): string {
  return window.localStorage.getItem(STORAGE_KEY) ?? DEFAULT_LANGUAGE;
}
