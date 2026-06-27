import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export default function CompleteProfile() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const [formData, setFormData] = useState({
    profession: 'student',
    workingHoursStart: '09:00',
    workingHoursEnd: '18:00',
    timezone: 'IST',
    sessionDuration: 60,
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');
      const displayName = localStorage.getItem('userDisplayName');

      const response = await fetch('http://localhost:8000/api/users/profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          profile_data: {
            name: displayName,
            profession: formData.profession,
            working_hours_start: formData.workingHoursStart,
            working_hours_end: formData.workingHoursEnd,
            productive_hours: [],
            preferred_session_duration: formData.sessionDuration,
            timezone: formData.timezone,
          },
          pref_data: {
            email_reminders: true,
            push_notifications: false,
            daily_summary: true,
          },
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to complete profile');
      }

      // Clear temp storage and redirect
      localStorage.removeItem('userEmail');
      localStorage.removeItem('userDisplayName');
      navigate('/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAF8] flex items-center justify-center p-4">
      <Card className="w-full max-w-md border-slate-200/50 bg-white/70 backdrop-blur-sm">
        <div className="p-8 space-y-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Complete Profile</h1>
            <p className="text-sm text-slate-600 mt-1">
              Just a few more details to get started
            </p>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Profession */}
            <div>
              <Label htmlFor="profession">I am a</Label>
              <Select
                value={formData.profession}
                onValueChange={(value) =>
                  setFormData((prev) => ({ ...prev, profession: value }))
                }
              >
                <SelectTrigger className="mt-1.5 h-10 border-slate-300">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="student">Student</SelectItem>
                  <SelectItem value="professional">Professional</SelectItem>
                  <SelectItem value="entrepreneur">Entrepreneur</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Timezone */}
            <div>
              <Label htmlFor="timezone">Timezone</Label>
              <Select
                value={formData.timezone}
                onValueChange={(value) =>
                  setFormData((prev) => ({ ...prev, timezone: value }))
                }
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

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full bg-slate-900 text-white hover:bg-slate-800 h-10 mt-6"
            >
              {isLoading ? 'Setting up...' : 'Continue to Dashboard'}
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
}