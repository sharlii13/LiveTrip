import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import { startTranslation } from "./lib/translate";
import { setUpPwa } from "./lib/pwa";

createRoot(document.getElementById("root")!).render(<App />);
startTranslation();
setUpPwa();
