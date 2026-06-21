import { useEffect, useState } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { bootstrapSession, apiGet } from './api.js';

import Home from './pages/Home.jsx';
import Login from './pages/Login.jsx';
import LoginPhone from './pages/LoginPhone.jsx';
import Signup from './pages/Signup.jsx';
import VerifyOtp from './pages/VerifyOtp.jsx';
import ForgotPassword from './pages/ForgotPassword.jsx';
import ResetPasswordVerify from './pages/ResetPasswordVerify.jsx';
import ResetPasswordNew from './pages/ResetPasswordNew.jsx';
import ClientDashboard from './pages/ClientDashboard.jsx';
import OrderSuccess from './pages/OrderSuccess.jsx';
import PaymentInitiate from './pages/PaymentInitiate.jsx';
import PaymentFailure from './pages/PaymentFailure.jsx';
import OrderWizard from './pages/OrderWizard.jsx';
import Policy from './pages/Policy.jsx';
import OrderDetail from './pages/OrderDetail.jsx';
import ClientPreview from './pages/ClientPreview.jsx';
import AdminDashboard from './pages/AdminDashboard.jsx';
import AdminLogin from './pages/AdminLogin.jsx';
import PilotDashboard from './pages/PilotDashboard.jsx';
import PilotExecute from './pages/PilotExecute.jsx';

// Pages not yet converted from the Flask templates render this notice.
function ComingSoon({ name }) {
  return (
    <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '0.75rem', fontFamily: 'Inter, sans-serif' }}>
      <h2 style={{ color: 'var(--navy)' }}>{name}</h2>
      <p style={{ color: 'var(--gray-500)' }}>This page is being migrated to the new frontend.</p>
      <a href="/" className="btn btn-primary">← Home</a>
    </div>
  );
}

function Logout() {
  const nav = useNavigate();
  useEffect(() => {
    apiGet('/logout').then(() => {
      window.dispatchEvent(new Event('auth-changed'));
      nav('/');
    });
  }, []);
  return null;
}

export default function App() {
  const [session, setSession] = useState(null);

  useEffect(() => {
    const load = () => bootstrapSession().then(setSession);
    load();
    window.addEventListener('auth-changed', load);
    return () => window.removeEventListener('auth-changed', load);
  }, []);

  if (!session) return null; // wait for CSRF token before rendering forms

  return (
    <Routes>
      <Route path="/" element={<Home session={session} />} />
      <Route path="/login" element={<Login />} />
      <Route path="/login/phone" element={<LoginPhone />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/verify-otp" element={<VerifyOtp />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password-verify" element={<ResetPasswordVerify />} />
      <Route path="/reset-password-new" element={<ResetPasswordNew />} />
      <Route path="/logout" element={<Logout />} />

      <Route path="/client/orders" element={<ClientDashboard session={session} />} />
      <Route path="/order/success" element={<OrderSuccess />} />
      <Route path="/payment/initiate" element={<PaymentInitiate />} />
      <Route path="/payment/failure-page" element={<PaymentFailure />} />

      <Route path="/order" element={<OrderWizard session={session} />} />
      <Route path="/order/:orderId/preview" element={<ClientPreview />} />
      <Route path="/order/:orderId" element={<OrderDetail session={session} />} />

      <Route path="/dq-control-7x9k" element={<AdminLogin />} />
      <Route path="/admin" element={<AdminDashboard session={session} />} />
      <Route path="/admin/dashboard" element={<AdminDashboard session={session} />} />
      <Route path="/pilot" element={<PilotDashboard />} />
      <Route path="/pilot/dashboard" element={<PilotDashboard />} />
      <Route path="/pilot/execute/:orderId" element={<PilotExecute />} />
      <Route path="/pilot/job/:orderId" element={<PilotExecute />} />

      {/* Next migration phases */}
      <Route path="/admin/*" element={<ComingSoon name="Admin Dashboard" />} />
      <Route path="/order/*" element={<ComingSoon name="Order" />} />
      <Route path="/about" element={<Policy page="about" session={session} />} />
      <Route path="/terms" element={<Policy page="terms" session={session} />} />
      <Route path="/privacy" element={<Policy page="privacy" session={session} />} />
      <Route path="/refund-policy" element={<Policy page="refund" session={session} />} />
      <Route path="/shipping-policy" element={<Policy page="shipping" session={session} />} />
      <Route path="*" element={<ComingSoon name="Page Not Found" />} />
    </Routes>
  );
}
