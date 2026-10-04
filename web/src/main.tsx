import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";
import { I18nProvider } from "./i18n";
import { LanguageProvider, Layout } from "./Layout";
import { BookPage } from "./pages/BookPage";
import { Library } from "./pages/Library";
import { Reader } from "./pages/Reader";
import { Review } from "./pages/Review";
import { SettingsPage } from "./pages/SettingsPage";
import { Vocabulary } from "./pages/Vocabulary";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <I18nProvider>
      <LanguageProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Library />} />
            <Route path="books/:bookId" element={<BookPage />} />
            <Route path="vocabulary" element={<Vocabulary />} />
            <Route path="review" element={<Review />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          {/* The reader is full screen, without the app header. */}
          <Route path="read/:sectionId" element={<Reader />} />
        </Routes>
      </LanguageProvider>
      </I18nProvider>
    </BrowserRouter>
  </StrictMode>,
);
