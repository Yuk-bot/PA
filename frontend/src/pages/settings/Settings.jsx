// src/pages/Settings.jsx

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { User, Bell, Zap, Calendar as CalendarIcon, Palette } from 'lucide-react';

export default function Settings() {
  const [formData, setFormData] = useState({
    name: 'Yukta',
    email: 'you@example.com',
    timezone: 'IST',
  });

  const [preferences, setPreferences] = useState({
    emailNotifications: true,
    pushNotifications: false,
    dailySummary: true,
    darkMode: false,
  });

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handlePreferenceChange = (field, value) => {
    setPreferences((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="p-6 md:p-8 space-y-8 max-w-2xl">
        {/* Header */}
        <div>
          <h2 className="text-3xl font-bold text-slate-900">Settings</h2>
          <p className="text-sm text-slate-600 mt-1">
            Manage your account and preferences
          </p>
        </div>

        {/* Profile Section */}
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
                  onChange={(e) => handleInputChange('name', e.target.value)}
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
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  className="mt-1.5 h-10 border-slate-300"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-slate-700">
                  Timezone
                </label>
                <Select value={formData.timezone}>
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

              <Button className="mt-4 bg-slate-900 text-white hover:bg-slate-800">
                Save Profile
              </Button>
            </div>
          </div>
        </Card>

        {/* Preferences Section */}
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
                  label: 'Email Notifications',
                  description: 'Receive email updates about tasks and reminders',
                  key: 'emailNotifications',
                },
                {
                  label: 'Push Notifications',
                  description: 'Get push notifications on your device',
                  key: 'pushNotifications',
                },
                {
                  label: 'Daily Summary',
                  description: 'Receive a daily summary of your productivity',
                  key: 'dailySummary',
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

        {/* Appearance Section */}
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
                  handlePreferenceChange('darkMode', value)
                }
              />
            </div>
          </div>
        </Card>

        {/* Integrations Section */}
        <Card className="border-slate-200/50 bg-white/70 backdrop-blur-sm p-6">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <CalendarIcon className="w-5 h-5 text-slate-600" />
              <h3 className="font-semibold text-slate-900">Integrations</h3>
            </div>

            <Separator />

            <div className="space-y-4">
              {[
                {
                  name: 'Google Calendar',
                  description: 'Sync your calendar events',
                  icon: CalendarIcon,
                  connected: false,
                },
                {
                  name: 'Gmail',
                  description: 'Extract tasks from emails',
                  icon: Zap,
                  connected: false,
                },
              ].map((integration) => (
                <div
                  key={integration.name}
                  className="flex items-center justify-between p-4 rounded-lg border border-slate-200/50 hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <integration.icon className="w-5 h-5 text-slate-600" />
                    <div>
                      <p className="font-medium text-slate-900">
                        {integration.name}
                      </p>
                      <p className="text-sm text-slate-600">
                        {integration.description}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant={integration.connected ? 'outline' : 'default'}
                    size="sm"
                    className={
                      integration.connected
                        ? 'text-slate-600'
                        : 'bg-slate-900 text-white hover:bg-slate-800'
                    }
                  >
                    {integration.connected ? 'Disconnect' : 'Connect'}
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* Danger Zone */}
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