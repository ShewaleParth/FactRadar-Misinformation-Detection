import MisinformationDetector from "./components/MisinformationDetector";
import { ThemeProvider } from "./components/ThemeContext";

export default function App() {
  return (
    <ThemeProvider>
      <MisinformationDetector />
    </ThemeProvider>
  );
}
