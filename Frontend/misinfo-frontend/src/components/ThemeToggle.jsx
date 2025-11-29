import React, { useContext } from "react";
import { Moon, Sun } from "lucide-react";
import { ThemeContext } from "./ThemeContext";

export default function ThemeToggle() {
  const { theme, setTheme } = useContext(ThemeContext);

  return (
    <button
      onClick={() => setTheme(theme === "light" ? "dark" : "light")}
      className="p-3 rounded-full bg-white dark:bg-gray-800 shadow-md 
                 border border-gray-200 dark:border-gray-700 transition"
    >
      {theme === "light" ? (
        <Moon className="w-6 h-6 text-gray-800" />
      ) : (
        <Sun className="w-6 h-6 text-yellow-300" />
      )}
    </button>
  );
}
