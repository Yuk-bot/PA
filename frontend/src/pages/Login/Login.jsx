

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
//import { useGoogleLogin } from '@react-oauth/google';
import { getAuth, signInWithEmailAndPassword } from 'firebase/auth';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Mail, Eye, EyeOff, ArrowLeft } from 'lucide-react';
import { GoogleAuthProvider, signInWithPopup } from 'firebase/auth';

export default function Login() {
  const navigate = useNavigate();
  const auth = getAuth();

  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});

  // Form state
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    // Clear error for this field when user starts typing
    if (errors[name]) {
      setErrors((prev) => ({
        ...prev,
        [name]: '',
      }));
    }
  };

  const handleEmailLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setErrors({});

    try {
      // Validation
      if (!formData.email) {
        setErrors({ email: 'Email is required' });
        setIsLoading(false);
        return;
      }
      if (!formData.password) {
        setErrors({ password: 'Password is required' });
        setIsLoading(false);
        return;
      }

      // Sign in with email and password
      const userCredential = await signInWithEmailAndPassword(
        auth,
        formData.email,
        formData.password
      );

      // Get Firebase ID token
      const idToken = await userCredential.user.getIdToken();

      // Store token
      localStorage.setItem('token', idToken);

      // Redirect to dashboard
      navigate('/dashboard');
    } catch (error) {
      const errorMessage = error.message || 'Login failed';

      // Firebase error messages
      if (error.code === 'auth/user-not-found') {
        setErrors({ email: 'No account found with this email' });
      } else if (error.code === 'auth/wrong-password') {
        setErrors({ password: 'Incorrect password' });
      } else if (error.code === 'auth/invalid-email') {
        setErrors({ email: 'Invalid email address' });
      } else if (error.code === 'auth/user-disabled') {
        setErrors({ email: 'This account has been disabled' });
      } else {
        setErrors({ general: errorMessage });
      }

      console.error('Login error:', error);
    } finally {
      setIsLoading(false);
    }
  };


 


const handleGoogleLogin = async () => {
  try {
    setIsLoading(true);
    setErrors({});

    const auth = getAuth();
    const provider = new GoogleAuthProvider();

    // Sign in with Google popup
    const result = await signInWithPopup(auth, provider);

    // Get Firebase ID token
    const idToken = await result.user.getIdToken();

    // Store token
    localStorage.setItem('token', idToken);

    // Redirect to dashboard
    navigate('/dashboard');
  } catch (error) {
    console.error('Google login error:', error);
    setErrors({
      general: error.message || 'Google login failed. Please try again.',
    });
  } finally {
    setIsLoading(false);
  }
};

  return (
    <div className="min-h-screen bg-[#FAFAF8] flex items-center justify-center p-4 relative">
      {/* Background Grid */}
      <svg
        className="fixed inset-0 -z-10 w-full h-full opacity-[0.08] pointer-events-none"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="none"
      >
        <defs>
          <pattern
            id="login-grid"
            width="40"
            height="40"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 40 0 L 0 0 0 40"
              fill="none"
              stroke="currentColor"
              strokeWidth="0.5"
              className="text-slate-900"
            />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#login-grid)" />
      </svg>

      {/* Back Button */}
      <Link
        to="/"
        className="absolute top-6 left-6 p-2 rounded-lg hover:bg-slate-100 transition-colors"
      >
        <ArrowLeft className="w-5 h-5 text-slate-600 hover:text-slate-900" />
      </Link>

      {/* Login Card */}
      <Card className="w-full max-w-md border-slate-200/50 bg-white/70 backdrop-blur-sm">
        <div className="p-8 space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Welcome Back</h1>
            <p className="text-sm text-slate-600 mt-1">
              Sign in to your PA account
            </p>
          </div>

          {/* General Error */}
          {errors.general && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{errors.general}</p>
            </div>
          )}

          {/* Google Sign In Button */}
          
<Button
  onClick={handleGoogleLogin}
  disabled={isLoading}
  variant="outline"
  className="w-full h-10 border-slate-300 hover:bg-slate-50"
>
  <Mail className="w-4 h-4 mr-2" />
  Continue with Google
</Button>

          {/* Divider */}
          <div className="relative">
            <Separator />
            <span className="absolute left-1/2 -translate-x-1/2 -top-2.5 bg-white px-2 text-xs text-slate-500">
              OR
            </span>
          </div>

          {/* Email/Password Form */}
          <form onSubmit={handleEmailLogin} className="space-y-4">
            {/* Email */}
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                name="email"
                type="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={handleInputChange}
                disabled={isLoading}
                className="mt-1.5 h-10 border-slate-300"
                autoFocus
              />
              {errors.email && (
                <p className="text-xs text-red-600 mt-1">{errors.email}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link
                  to="/forgot-password"
                  className="text-xs text-slate-600 hover:text-slate-900 transition-colors"
                >
                  Forgot?
                </Link>
              </div>
              <div className="relative mt-1.5">
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={handleInputChange}
                  disabled={isLoading}
                  className="h-10 border-slate-300 pr-10"
                  onKeyPress={(e) =>
                    e.key === 'Enter' && !isLoading && handleEmailLogin(e)
                  }
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={isLoading}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-700 disabled:opacity-50"
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-red-600 mt-1">{errors.password}</p>
              )}
            </div>

            {/* Sign In Button */}
            <Button
              type="submit"
              disabled={isLoading}
              className="w-full h-10 bg-slate-900 text-white hover:bg-slate-800 mt-6"
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          {/* Signup Link */}
          <p className="text-center text-sm text-slate-600">
            Don't have an account?{' '}
            <Link
              to="/signup"
              className="font-medium text-slate-900 hover:text-slate-700 transition-colors"
            >
              Sign up
            </Link>
          </p>
        </div>
      </Card>
    </div>
  );
}