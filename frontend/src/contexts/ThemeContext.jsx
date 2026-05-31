import React, { createContext, useState, useEffect, useContext } from 'react';

// 1. Create the Context
const ThemeContext = createContext();

// 2. Create the Provider Component
export const ThemeProvider = ({ children }) => {
    // Check local storage for a saved theme, default to 'dark'
    const [theme, setTheme] = useState(() => {
        return localStorage.getItem('app-theme') || 'dark';
    });

    useEffect(() => {
        // Whenever the theme changes, update the data-attribute on the HTML tag
        document.documentElement.setAttribute('data-theme', theme);
        // Save the preference to local storage
        localStorage.setItem('app-theme', theme);
    }, [theme]);

    const toggleTheme = () => {
        setTheme((prevTheme) => {
            const newTheme = prevTheme === 'light' ? 'dark' : 'light';
            console.log("🔥 Theme changing to:", newTheme);
            return newTheme;
        });
    };

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme }}>
            {children}
        </ThemeContext.Provider>
    );
};

// 3. Custom hook to make using the theme easier
export const useTheme = () => useContext(ThemeContext);