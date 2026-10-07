import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { AuthProvider } from "./auth";
import { I18nProvider } from "./i18n";
import { LanguageProvider, Layout } from "./Layout";
import { BookPage } from "./pages/BookPage";
import { Library } from "./pages/Library";
import { Reader } from "./pages/Reader";
import { Extras } from "./pages/Extras";
import { Drills } from "./pages/Drills";
import { DrillRound } from "./pages/DrillRound";
import { Review } from "./pages/Review";
import { SettingsPage } from "./pages/SettingsPage";
import { Vocabulary } from "./pages/Vocabulary";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <I18nProvider>
      <AuthProvider>
      <LanguageProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Library />} />
            <Route path="books/:bookId" element={<BookPage />} />
            <Route path="vocabulary" element={<Vocabulary />} />
            <Route path="review" element={<Review />} />
            <Route path="drills" element={<Drills />} />
            <Route path="drills/:roundId" element={<DrillRound />} />
            <Route path="extras" element={<Extras />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          {/* An invitation link opened while already signed in. */}
          <Route path="join/:code" element={<Navigate to="/" replace />} />
          {/* The reader is full screen, without the app header. */}
          <Route path="read/:sectionId" element={<Reader />} />
        </Routes>
      </LanguageProvider>
      </AuthProvider>
      </I18nProvider>
    </BrowserRouter>
  </StrictMode>,
);
