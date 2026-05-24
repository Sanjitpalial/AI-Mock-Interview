import React from 'react';
import '@radix-ui/themes/styles.css';
import { Theme } from '@radix-ui/themes';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import { AuthProvider } from './context/AuthContext';
import Home from './pages/Home';
import MockInterview from './pages/MockInterview';
import StudyAssistant from './pages/StudyAssistant';
import Analytics from './pages/Analytics';
import Profile from './pages/Profile';
import History from './pages/History';
import Login from './pages/Login';
import Register from './pages/Register';
import NotFound from './pages/NotFound';

const App = () => {
  return (
    <Theme appearance="dark" radius="large" scaling="100%">
      <AuthProvider>
      <Router>
        <main className="min-h-screen font-sans selection:bg-primary/10 selection:text-primary">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/interview" element={<MockInterview />} />
            <Route path="/study" element={<StudyAssistant />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/history" element={<History />} />
            <Route path="/history/:id" element={<History />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="*" element={<NotFound />} />
          </Routes>

          <ToastContainer
            position="top-right"
            autoClose={3000}
            hideProgressBar={false}
            newestOnTop
            closeOnClick
            rtl={false}
            pauseOnFocusLoss
            draggable
            pauseOnHover
            theme="dark"
          />
        </main>
      </Router>
      </AuthProvider>
    </Theme>
  );
};

export default App;