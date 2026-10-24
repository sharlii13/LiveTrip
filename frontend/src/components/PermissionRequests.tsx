import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MapPin, Bell, X, CheckCircle } from 'lucide-react';

interface PermissionRequestsProps {
  onComplete: () => void;
}

export default function PermissionRequests({ onComplete }: PermissionRequestsProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [locationGranted, setLocationGranted] = useState(false);
  const [notificationGranted, setNotificationGranted] = useState(false);
  const [isVisible, setIsVisible] = useState(true);

  const steps = [
    {
      id: 'location',
      title: 'Location Access',
      description: 'Allow LiveTrip to access your location for better recommendations and local experiences',
      icon: MapPin,
      action: 'Enable Location',
      color: 'blue'
    },
    {
      id: 'notifications',
      title: 'Notifications',
      description: 'Get notified about travel deals, trip updates, and personalized recommendations',
      icon: Bell,
      action: 'Enable Notifications',
      color: 'green'
    }
  ];

  const currentStepData = steps[currentStep];

  const handlePermissionRequest = async () => {
    if (currentStepData.id === 'location') {
      try {
        if (navigator.geolocation) {
          navigator.geolocation.getCurrentPosition(
            (position) => {
              console.log('Location granted:', position);
              setLocationGranted(true);
              setTimeout(() => setCurrentStep(1), 1000);
            },
            (error) => {
              console.log('Location denied:', error);
              setLocationGranted(false);
              setTimeout(() => setCurrentStep(1), 1000);
            }
          );
        } else {
          console.log('Geolocation not supported');
          setLocationGranted(false);
          setTimeout(() => setCurrentStep(1), 1000);
        }
      } catch (error) {
        console.log('Location error:', error);
        setLocationGranted(false);
        setTimeout(() => setCurrentStep(1), 1000);
      }
    } else if (currentStepData.id === 'notifications') {
      try {
        if ('Notification' in window) {
          const permission = await Notification.requestPermission();
          if (permission === 'granted') {
            console.log('Notifications granted');
            setNotificationGranted(true);
          } else {
            console.log('Notifications denied');
            setNotificationGranted(false);
          }
        } else {
          console.log('Notifications not supported');
          setNotificationGranted(false);
        }
        setTimeout(() => {
          setIsVisible(false);
          onComplete();
        }, 1000);
      } catch (error) {
        console.log('Notification error:', error);
        setNotificationGranted(false);
        setTimeout(() => {
          setIsVisible(false);
          onComplete();
        }, 1000);
      }
    }
  };

  const handleSkip = () => {
    if (currentStep === 0) {
      setLocationGranted(false);
      setCurrentStep(1);
    } else {
      setNotificationGranted(false);
      setIsVisible(false);
      onComplete();
    }
  };

  const handleClose = () => {
    setIsVisible(false);
    onComplete();
  };

  // For testing - add to window object
  useEffect(() => {
    (window as any).resetPermissions = () => {
      localStorage.removeItem('liveTrip-permissions-requested');
      window.location.reload();
    };
  }, []);

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-md mx-auto animate-in slide-in-from-bottom-4 duration-300">
        <CardHeader className="text-center relative">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClose}
            className="absolute right-2 top-2 h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
          
          <div className="flex justify-center mb-4">
            <div className={`w-16 h-16 rounded-full flex items-center justify-center ${
              currentStepData.color === 'blue' ? 'bg-brand-100' : 'bg-brand-100'
            }`}>
              <currentStepData.icon className={`w-8 h-8 ${
                currentStepData.color === 'blue' ? 'text-brand-700' : 'text-brand-700'
              }`} />
            </div>
          </div>
          
          <CardTitle className="text-xl font-bold">
            {currentStepData.title}
          </CardTitle>
          <CardDescription className="text-base">
            {currentStepData.description}
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {/* Progress indicator */}
          <div className="flex justify-center space-x-2">
            {steps.map((_, index) => (
              <div
                key={index}
                className={`w-2 h-2 rounded-full ${
                  index <= currentStep ? 'bg-brand-700' : 'bg-gray-300'
                }`}
              />
            ))}
          </div>

          {/* Success message */}
          {(currentStepData.id === 'location' && locationGranted) || 
           (currentStepData.id === 'notifications' && notificationGranted) ? (
            <div className="text-center py-4">
              <CheckCircle className="w-12 h-12 text-brand-700 mx-auto mb-2" />
              <p className="text-brand-700 font-medium">
                {currentStepData.title} Enabled!
              </p>
            </div>
          ) : (
            <div className="flex space-x-3">
              <Button
                onClick={handlePermissionRequest}
                className={`flex-1 ${
                  currentStepData.color === 'blue' 
                    ? 'bg-brand-700 hover:bg-brand-800' 
                    : 'bg-brand-700 hover:bg-brand-800'
                }`}
              >
                {currentStepData.action}
              </Button>
              <Button
                variant="outline"
                onClick={handleSkip}
                className="flex-1"
              >
                Skip
              </Button>
            </div>
          )}

          {/* Step indicator */}
          <div className="text-center text-sm text-gray-500">
            Step {currentStep + 1} of {steps.length}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
