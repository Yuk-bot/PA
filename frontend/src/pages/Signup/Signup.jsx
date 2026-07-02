
import { auth } from "@/lib/firebase";

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Mail, ArrowLeft, Eye, EyeOff } from 'lucide-react';
import { API_BASE } from "@/services/apiConfig";


import {
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  signInWithPopup,
} from "firebase/auth";

export default function Signup() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
    profession: '',           
    timezone: '',             
    workingHoursStart: '',    
    workingHoursEnd: '',      
    sessionDuration: '',
    productiveHours: ["09:00-11:00"],
    
  });

  // Error state
  const [errors, setErrors] = useState({})

//google signup

const handleGoogleSignup = async () => {
  setIsLoading(true);

  try {
    const provider = new GoogleAuthProvider();

    const result = await signInWithPopup(auth, provider);

    const user = result.user;
    const token = await user.getIdToken();
    //console.log("UID:", user.uid);
    //console.log("TOKEN:", token);
    //console.log("TOKEN LENGTH:", token.length);

    localStorage.setItem("token", token);
    localStorage.setItem("userDisplayName", user.displayName);

    //console.log(localStorage.getItem("token"));
    //console.log("Firebase user:", user);
    //console.log("displayName:", user.displayName);
    

    // Create Firestore profile if first login
    const response = await fetch(`${API_BASE}/users/profile`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    profile_data: {
      name: user.displayName,
      profession: formData.profession,
      working_hours_start: formData.workingHoursStart,
      working_hours_end: formData.workingHoursEnd,
      productive_hours: ["09:00-11:00", "14:00-16:00"],
      preferred_session_duration: formData.sessionDuration,
      timezone: formData.timezone,
      productive_hours: formData.productiveHours,
    },
    pref_data: {
      email_reminders: true,
      push_notifications: false,
      daily_summary: true,
    },
  }),
});

navigate("/profile");
  } catch (error) {
    console.error(error);

    setErrors({
      email: error.message || "Google signup failed.",
    });
  } finally {
    setIsLoading(false);
  }

  
};



const validateForm = () => {
  const newErrors = {};

  if (!formData.fullName.trim()) {
    newErrors.fullName = "Full name is required";
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (!formData.email.trim()) {
    newErrors.email = "Email is required";
  } else if (!emailRegex.test(formData.email)) {
    newErrors.email = "Please enter a valid email";
  }

  if (!formData.password) {
    newErrors.password = "Password is required";
  } else if (formData.password.length < 8) {
    newErrors.password = "Password must be at least 8 characters";
  }

  if (!formData.confirmPassword) {
    newErrors.confirmPassword = "Please confirm your password";
  } else if (formData.password !== formData.confirmPassword) {
    newErrors.confirmPassword = "Passwords do not match";
  }

  setErrors(newErrors);

  return Object.keys(newErrors).length === 0;
};



const handleInputChange = (e) => {
  const { name, value } = e.target;

  setFormData((prev) => ({
    ...prev,
    [name]: value,
  }));

  if (errors[name]) {
    setErrors((prev) => ({
      ...prev,
      [name]: "",
    }));
  }
};



const handleEmailSignup = async (e) => {
  e.preventDefault();

  if (!validateForm()) return;

  setIsLoading(true);

  try {
    const userCredential = await createUserWithEmailAndPassword(
      auth,
      formData.email,
      formData.password
    );

    const user = userCredential.user;

    const token = await user.getIdToken();

    localStorage.setItem("token", token);

    // Create Firestore profile
    await fetch(`${API_BASE}/users/profile`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        profile_data: {
          name: formData.fullName,
          profession: formData.profession || "student",
          working_hours_start: formData.workingHoursStart || "09:00",
          working_hours_end: formData.workingHoursEnd || "18:00",
          productive_hours: formData.productiveHours || ["09:00-11:00"],
          preferred_session_duration: parseInt(formData.sessionDuration) || 60,
          timezone: formData.timezone || "IST",
        },
        pref_data: {
          email_reminders: true,
          push_notifications: false,
          daily_summary: true,
        },
      }),
    });

    navigate("/dashboard");
  } catch (error) {
    console.error(error);

    setErrors({
      email: error.message,
    });
  } finally {
    setIsLoading(false);
  }
};



const isFormValid =
  formData.fullName.trim() &&
  formData.email &&
  formData.password &&
  formData.password === formData.confirmPassword &&
  formData.password.length >= 8 &&
  !errors.email &&
  !errors.password &&
  !errors.confirmPassword;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12 bg-[#FAFAF8]">
      {/* Subtle grid background */}
      <svg
        className="fixed inset-0 -z-10 w-full h-full opacity-[0.08]"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="none"
      >
        <defs>
          <pattern
            id="signup-grid"
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
        <rect width="100%" height="100%" fill="url(#signup-grid)" />
      </svg>

      {/* Back button */}
      <button
        onClick={() => navigate('/')}
        className="absolute top-6 left-6 p-2 hover:bg-slate-100 rounded-lg transition-colors"
      >
        <ArrowLeft className="w-5 h-5 text-slate-600" />
      </button>

      {/* Main Card */}
      <Card className="w-full max-w-md border-slate-200/50 bg-white/70 backdrop-blur-sm shadow-sm">
        <div className="p-8 sm:p-10">
          {/* Header */}
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Create Account</h1>
            <p className="text-sm text-slate-600">
              Join PA and organize your productivity
            </p>
          </div>

          {/* Google Sign Up Button */}
          <Button
            onClick={handleGoogleSignup}
            disabled={isLoading}
            variant="outline"
            size="lg"
            className="w-full border-slate-300 text-slate-900 hover:bg-slate-50 mb-6 h-11"
          >
            <Mail className="w-4 h-4 mr-2" />
            Continue with Google
          </Button>

          {/* Divider */}
          <div className="mb-6 flex items-center gap-3">
            <Separator className="flex-1" />
            <span className="text-xs text-slate-500 font-medium">OR</span>
            <Separator className="flex-1" />
          </div>

          {/* Email/Password Form */}
          <form onSubmit={handleEmailSignup} className="space-y-4">
            {/* Full Name */}
            <div className="space-y-2">
              <Label htmlFor="fullName" className="text-sm font-medium text-slate-700">
                Full Name
              </Label>
              <Input
                id="fullName"
                name="fullName"
                type="text"
                placeholder="John Doe"
                value={formData.fullName}
                onChange={handleInputChange}
                disabled={isLoading}
                className="h-10 border-slate-300 bg-white text-slate-900 placeholder:text-slate-400"
              />
              {errors.fullName && (
                <p className="text-xs text-red-600 mt-1">{errors.fullName}</p>
              )}
            </div>

            {/* Email */}
            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm font-medium text-slate-700">
                Email
              </Label>
              <Input
                id="email"
                name="email"
                type="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={handleInputChange}
                disabled={isLoading}
                className="h-10 border-slate-300 bg-white text-slate-900 placeholder:text-slate-400"
              />
              {errors.email && (
                <p className="text-xs text-red-600 mt-1">{errors.email}</p>
              )}
            </div>

            {/* Profession */}

<div>
  <Label htmlFor="profession">I am a</Label>
  <Select value={formData.profession} onValueChange={(value) => setFormData(prev => ({ ...prev, profession: value }))}>
    <SelectTrigger className="mt-1.5 h-10 border-slate-300">
      <SelectValue />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="student">Student</SelectItem>
      <SelectItem value="professional">Professional</SelectItem>
    </SelectContent>
  </Select>
</div>

{/* Timezone */}
<div>
  <Label htmlFor="timezone">Timezone</Label>
  <Select value={formData.timezone} onValueChange={(value) => setFormData(prev => ({ ...prev, timezone: value }))}>
    <SelectTrigger className="mt-1.5 h-10 border-slate-300">
      <SelectValue />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="IST">IST (India)</SelectItem>
      <SelectItem value="UTC">UTC</SelectItem>
    </SelectContent>
  </Select>
</div>

{/* Working Hours Start */}
<div>
  <Label htmlFor="workingHoursStart">Work Start Time</Label>
  <Input
    id="workingHoursStart"
    name="workingHoursStart"
    type="time"
    value={formData.workingHoursStart}
    onChange={handleInputChange}
    className="mt-1.5 h-10 border-slate-300"
  />
</div>

{/* Working Hours End */}
<div>
  <Label htmlFor="workingHoursEnd">Work End Time</Label>
  <Input
    id="workingHoursEnd"
    name="workingHoursEnd"
    type="time"
    value={formData.workingHoursEnd}
    onChange={handleInputChange}
    className="mt-1.5 h-10 border-slate-300"
  />
</div>

{/* Session Duration */}
<div>
  <Label htmlFor="sessionDuration">Session Duration (minutes)</Label>
  <Input
    id="sessionDuration"
    name="sessionDuration"
    type="number"
    value={formData.sessionDuration}
    onChange={handleInputChange}
    className="mt-1.5 h-10 border-slate-300"
  />
</div>
{/* Productive Hours */}
<div>
  <Label>Peak Productive Hours</Label>
  <Input
    name="productiveHours"
    placeholder="e.g., 09:00-11:00, 14:00-16:00"
    value={formData.productiveHours.join(', ')}
    onChange={(e) => setFormData(prev => ({
      ...prev,
      productiveHours: e.target.value.split(',').map(h => h.trim())
    }))}
    className="mt-1.5 h-10 border-slate-300"
  />
  <p className="text-xs text-slate-500 mt-1">Comma-separated time ranges</p>
</div>

            {/* Password */}
            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm font-medium text-slate-700">
                Password
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="At least 8 characters"
                  value={formData.password}
                  onChange={handleInputChange}
                  disabled={isLoading}
                  className="h-10 border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-700"
                  disabled={isLoading}
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

            {/* Confirm Password */}
            <div className="space-y-2">
              <Label htmlFor="confirmPassword" className="text-sm font-medium text-slate-700">
                Confirm Password
              </Label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  placeholder="Confirm your password"
                  value={formData.confirmPassword}
                  onChange={handleInputChange}
                  disabled={isLoading}
                  className="h-10 border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-700"
                  disabled={isLoading}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
              {errors.confirmPassword && (
                <p className="text-xs text-red-600 mt-1">{errors.confirmPassword}</p>
              )}
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              disabled={!isFormValid || isLoading}
              size="lg"
              className="w-full bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed mt-6 h-11"
            >
              {isLoading ? 'Creating Account...' : 'Create Account'}
            </Button>
          </form>

          {/* Footer */}
          <p className="text-center text-sm text-slate-600 mt-6">
            Already have an account?{' '}
            <Link
              to="/login"
              className="font-medium text-slate-900 hover:text-slate-700 transition-colors"
            >
              Sign In
            </Link>
          </p>
        </div>
      </Card>
    </div>
  );
}