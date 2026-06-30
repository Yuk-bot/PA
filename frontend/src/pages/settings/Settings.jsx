import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  User,
  Bell,
  Zap,
  Calendar as CalendarIcon,
  Palette,
  Mail,
  Loader,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import {
  checkGmailStatus,
  connectGmail,
  disconnectGmail,
} from "@/services/gmailService";

export default function Settings() {
  const token = localStorage.getItem("token");
  const [searchParams, setSearchParams] = useSearchParams();

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    timezone: "IST",
  });

  const [preferences, setPreferences] = useState({
    emailNotifications: true,
    pushNotifications: false,
    dailySummary: true,
    darkMode: false,
  });

  const [isCalendarConnected, setIsCalendarConnected] = useState(false);
  const [isGmailConnected, setIsGmailConnected] = useState(false);
  const [connectedEmail, setConnectedEmail] = useState("");
  const [isStatusLoading, setIsStatusLoading] = useState(true);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);

  const oauthConnected = searchParams.get("calendar_connected");
  const oauthError = searchParams.get("error");
  const oauthEmail = searchParams.get("email");

  const showToast = (message, type = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const loadProfile = async () => {
    if (!token) return;
    try {
      const res = await fetch("http://localhost:8000/api/users/profile", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setFormData({
          name: data.profile?.name || "",
          email: data.email || "",
          timezone: data.profile?.timezone || "IST",
        });
        setPreferences({
          emailNotifications: data.preferences?.email_reminders ?? true,
          pushNotifications: data.preferences?.push_notifications ?? false,
          dailySummary: data.preferences?.daily_summary ?? true,
          darkMode: preferences.darkMode,
        });
      }
    } catch (e) { }
  };

  const checkStatus = async () => {
    if (!token) return;
    setError("");
    try {
      const status = await checkGmailStatus(token);
      setIsCalendarConnected(status.connected);
      setIsGmailConnected(status.connected);
      setConnectedEmail(status.email || "");
    } catch (err) {
      setError(err.message || "Failed to load connection status");
    } finally {
      setIsStatusLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
    checkStatus();
  }, [token]);

  useEffect(() => {
    if (oauthConnected === "true") {
      setIsCalendarConnected(true);
      setIsGmailConnected(true);
      if (oauthEmail) {
        setConnectedEmail(oauthEmail);
      }
      showToast("Connected successfully");
      setSearchParams({}, { replace: true });
      checkStatus();
    } else if (oauthError) {
      const readable =
        oauthError === "missing_code"
          ? "OAuth cancelled"
          : "Network error";
      setError(readable);
      showToast(readable, "error");
      setSearchParams({}, { replace: true });
    }
  }, [oauthConnected, oauthError, oauthEmail]);

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handlePreferenceChange = (field, value) => {
    setPreferences((prev) => ({ ...prev, [field]: value }));
  };

  const handleConnect = async () => {
    if (!token) return;
    setIsStatusLoading(true);
    setError("");
    try {
      const { authorization_url } = await connectGmail(token);
      window.location.href = authorization_url;
    } catch (err) {
      setError(err.message || "Failed to initiate connection");
      showToast("Failed to initiate connection", "error");
      setIsStatusLoading(false);
    }
  };

  const handleDisconnect = async () => {
    if (!token) return;
    setIsStatusLoading(true);
    setError("");
    try {
      await disconnectGmail(token);
      setIsCalendarConnected(false);
      setIsGmailConnected(false);
      setConnectedEmail("");
      showToast("Disconnected successfully");
    } catch (err) {
      setError(err.message || "Failed to disconnect");
      showToast("Failed to disconnect", "error");
    } finally {
      setIsStatusLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    if (!token) return;
    try {
      const res = await fetch("http://localhost:8000/api/users/profile", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          profile_data: {
            name: formData.name,
            profession: "professional",
            working_hours_start: "09:00",
            working_hours_end: "18:00",
            productive_hours: ["09:00-11:00"],
            preferred_session_duration: 60,
            timezone: formData.timezone,
          },
          pref_data: {
            email_reminders: preferences.emailNotifications,
            push_notifications: preferences.pushNotifications,
            daily_summary: preferences.dailySummary,
          },
        }),
      });
      if (res.ok) {
        showToast("Profile updated successfully");
      } else {
        showToast("Failed to update profile", "error");
      }
    } catch (e) {
      showToast("Failed to update profile", "error");
    }
  };

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="p-6 md:p-8 space-y-8 max-w-2xl">
        <div>
          <h2 className="text-3xl font-bold text-slate-900">Settings</h2>
          <p className="text-sm text-slate-600 mt-1">
            Manage your account and preferences
          </p>
        </div>

        {toast && (
          <div
            className={`fixed top-4 right-4 z-50 flex items-center gap-2 p-4 rounded-lg shadow-lg border text-sm animate-in fade-in slide-in-from-top-4 duration-200 ${toast.type === "error"
                ? "bg-red-50 border-red-200 text-red-800"
                : toast.type === "info"
                  ? "bg-blue-50 border-blue-200 text-blue-800"
                  : "bg-emerald-50 border-emerald-200 text-emerald-800"
              }`}
          >
            {toast.type === "error" ? (
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
            ) : toast.type === "info" ? (
              <Loader className="w-4 h-4 text-blue-600 shrink-0 animate-spin" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            )}
            <span>{toast.message}</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm p-6">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-slate-600" />
              <h3 className="font-semibold text-slate-900">Profile</h3>
            </div>

            <Separator />

            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-slate-700">
                  Full Name
                </label>
                <Input
                  value={formData.name}
                  onChange={(e) => handleInputChange("name", e.target.value)}
                  className="mt-1.5 h-10 border-slate-300"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-slate-700">
                  Email
                </label>
                <Input
                  type="email"
                  value={formData.email}
                  disabled
                  className="mt-1.5 h-10 border-slate-300 bg-slate-50"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-slate-700">
                  Timezone
                </label>
                <Select
                  value={formData.timezone}
                  onValueChange={(val) => handleInputChange("timezone", val)}
                >
                  <SelectTrigger className="mt-1.5 h-10 border-slate-300">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="IST">IST (India)</SelectItem>
                    <SelectItem value="UTC">UTC</SelectItem>
                    <SelectItem value="EST">EST (US Eastern)</SelectItem>
                    <SelectItem value="PST">PST (US Pacific)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button
                onClick={handleSaveProfile}
                className="mt-4 bg-slate-900 text-white hover:bg-slate-800"
              >
                Save Profile
              </Button>
            </div>
          </div>
        </Card>

        <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm p-6">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <Bell className="w-5 h-5 text-slate-600" />
              <h3 className="font-semibold text-slate-900">Notifications</h3>
            </div>

            <Separator />

            <div className="space-y-4">
              {[
                {
                  label: "Email Notifications",
                  description: "Receive email updates about tasks and reminders",
                  key: "emailNotifications",
                },
                {
                  label: "Push Notifications",
                  description: "Get push notifications on your device",
                  key: "pushNotifications",
                },
                {
                  label: "Daily Summary",
                  description: "Receive a daily summary of your productivity",
                  key: "dailySummary",
                },
              ].map((pref) => (
                <div
                  key={pref.key}
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  <div className="flex-1">
                    <p className="font-medium text-slate-900">{pref.label}</p>
                    <p className="text-sm text-slate-600 mt-0.5">
                      {pref.description}
                    </p>
                  </div>
                  <Switch
                    checked={preferences[pref.key]}
                    onCheckedChange={(value) =>
                      handlePreferenceChange(pref.key, value)
                    }
                  />
                </div>
              ))}
            </div>
          </div>
        </Card>

        <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm p-6">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <Palette className="w-5 h-5 text-slate-600" />
              <h3 className="font-semibold text-slate-900">Appearance</h3>
            </div>

            <Separator />

            <div className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50 transition-colors">
              <div>
                <p className="font-medium text-slate-900">Dark Mode</p>
                <p className="text-sm text-slate-600 mt-0.5">
                  Use dark theme for the app
                </p>
              </div>
              <Switch
                checked={preferences.darkMode}
                onCheckedChange={(value) =>
                  handlePreferenceChange("darkMode", value)
                }
              />
            </div>
          </div>
        </Card>

        <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm p-6">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <CalendarIcon className="w-5 h-5 text-slate-600" />
              <h3 className="font-semibold text-slate-900">Google Calendar Integration</h3>
            </div>

            <Separator />

            {isStatusLoading ? (
              <div className="space-y-3 animate-pulse">
                <div className="h-4 bg-slate-200 rounded w-1/4" />
                <div className="h-10 bg-slate-100 rounded w-full" />
              </div>
            ) : isCalendarConnected ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-lg border border-slate-200/50 bg-slate-50/50">
                  <div className="flex items-center gap-3">
                    <CalendarIcon className="w-5 h-5 text-slate-600" />
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-slate-900">
                          Google Calendar
                        </p>
                        <span className="text-[10px] font-semibold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">
                          Connected
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {connectedEmail}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDisconnect}
                    className="text-red-600 border-red-200 hover:bg-red-50"
                  >
                    Disconnect
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-lg border border-slate-200/50">
                  <div className="flex items-center gap-3">
                    <CalendarIcon className="w-5 h-5 text-slate-400" />
                    <div>
                      <p className="font-medium text-slate-900">
                        Google Calendar
                      </p>
                      <p className="text-sm text-slate-500">
                        Sync your calendar events with PA
                      </p>
                    </div>
                  </div>
                  <Button
                    onClick={handleConnect}
                    size="sm"
                    className="bg-slate-900 text-white hover:bg-slate-800"
                  >
                    Connect
                  </Button>
                </div>
              </div>
            )}
          </div>
        </Card>

        <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm p-6">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-slate-600" />
              <h3 className="font-semibold text-slate-900">Gmail Integration</h3>
            </div>

            <Separator />

            {isStatusLoading ? (
              <div className="space-y-3 animate-pulse">
                <div className="h-4 bg-slate-200 rounded w-1/4" />
                <div className="h-10 bg-slate-100 rounded w-full" />
              </div>
            ) : isGmailConnected ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-lg border border-slate-200/50 bg-slate-50/50">
                  <div className="flex items-center gap-3">
                    <Mail className="w-5 h-5 text-slate-600" />
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-slate-900">Gmail</p>
                        <span className="text-[10px] font-semibold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">
                          Connected
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {connectedEmail}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDisconnect}
                    className="text-red-600 border-red-200 hover:bg-red-50"
                  >
                    Disconnect
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-5 rounded-lg border border-slate-200/50 bg-slate-50/30 gap-4">
                  <div className="flex items-start gap-3">
                    <Mail className="w-5 h-5 text-slate-400 mt-0.5" />
                    <div>
                      <p className="font-semibold text-slate-950 text-sm">
                        Gmail Integration
                      </p>
                      <p className="text-xs text-slate-600 mt-1 max-w-sm">
                        Allow PA to read Gmail to extract actionable task
                        suggestions. This happens securely and completely
                        locally.
                      </p>
                    </div>
                  </div>
                  <Button
                    onClick={handleConnect}
                    size="sm"
                    className="bg-slate-900 text-white hover:bg-slate-800 self-start sm:self-center"
                  >
                    Connect Gmail
                  </Button>
                </div>
              </div>
            )}
          </div>
        </Card>

        <Card className="border-red-200/50 bg-red-50/50 p-6">
          <div className="space-y-6">
            <h3 className="font-semibold text-red-900">Danger Zone</h3>
            <Separator />
            <Button
              variant="outline"
              className="border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700"
            >
              Delete Account
            </Button>
          </div>
        </Card>
      </div>
    </main>
  );
}