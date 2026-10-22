import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Calendar } from '@/components/ui/calendar';
import { Badge } from '@/components/ui/badge';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useTripPlanning } from '@/contexts/TripPlanningContext';
import ProgressIndicator from '@/components/ProgressIndicator';

const DateSelection: React.FC = () => {
  const navigate = useNavigate();
  const { tripData, updateTripData, currentStep, totalSteps } = useTripPlanning();
  const [selectedDates, setSelectedDates] = useState<{ from: Date | undefined; to: Date | undefined }>({
    from: tripData.startDate || undefined,
    to: tripData.endDate || undefined,
  });

  const handleDateSelect = (date: Date | undefined) => {
    if (!date) return;

    if (!selectedDates.from || (selectedDates.from && selectedDates.to)) {
      // Start new selection
      setSelectedDates({ from: date, to: undefined });
    } else if (selectedDates.from && !selectedDates.to) {
      // Complete selection
      if (date < selectedDates.from) {
        setSelectedDates({ from: date, to: selectedDates.from });
      } else {
        setSelectedDates({ from: selectedDates.from, to: date });
      }
    }
  };

  const handleNext = () => {
    if (selectedDates.from && selectedDates.to) {
      updateTripData({
        startDate: selectedDates.from,
        endDate: selectedDates.to,
      });
      navigate('/trip-planning/company');
    }
  };

  const handleBack = () => {
    navigate('/search');
  };

  const getDuration = () => {
    if (selectedDates.from && selectedDates.to) {
      const diffTime = Math.abs(selectedDates.to.getTime() - selectedDates.from.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
      return diffDays;
    }
    return 0;
  };

  const isDateDisabled = (date: Date) => {
    return date < new Date(new Date().setHours(0, 0, 0, 0));  // today is allowed
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <ProgressIndicator 
        currentStep={currentStep} 
        totalSteps={totalSteps} 
        tripName={`${tripData.destination} trip`}
      />
      
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Card className="w-full">
          <CardHeader className="text-center">
            <CardTitle className="text-3xl font-bold text-blue-800 mb-2">
              When are you going?
            </CardTitle>
            <CardDescription className="text-lg text-gray-600">
              Choose a date range, up to 7 days
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-6">
            <div className="flex justify-center">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Calendar */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-blue-800">Select Dates</h3>
                    <div className="flex space-x-2">
                      <Button variant="outline" size="sm">
                        <ChevronLeft className="w-4 h-4" />
                      </Button>
                      <Button variant="outline" size="sm">
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                  
                  <Calendar
                    mode="range"
                    selected={selectedDates}
                    onSelect={(range) => {
                      if (range?.from) {
                        handleDateSelect(range.from);
                      }
                      if (range?.to) {
                        handleDateSelect(range.to);
                      }
                    }}
                    disabled={isDateDisabled}
                    className="rounded-md border"
                  />
                </div>

                {/* Selection Summary */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-blue-800">Trip Summary</h3>
                  
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Destination:</span>
                      <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                        {tripData.destination}
                      </Badge>
                    </div>
                    
                    {selectedDates.from && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">Start Date:</span>
                        <span className="font-medium">
                          {selectedDates.from.toLocaleDateString()}
                        </span>
                      </div>
                    )}
                    
                    {selectedDates.to && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">End Date:</span>
                        <span className="font-medium">
                          {selectedDates.to.toLocaleDateString()}
                        </span>
                      </div>
                    )}
                    
                    {getDuration() > 0 && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">Duration:</span>
                        <Badge variant="outline" className="bg-blue-50 text-blue-800">
                          {getDuration()} day{getDuration() > 1 ? 's' : ''}
                        </Badge>
                      </div>
                    )}
                  </div>

                  {getDuration() > 7 && (
                    <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                      <p className="text-sm text-yellow-800">
                        ⚠️ Trip duration exceeds 7 days. Please select a shorter range.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Navigation */}
            <div className="flex justify-between pt-6">
              <Button variant="outline" onClick={handleBack}>
                Back
              </Button>
              
              <Button 
                onClick={handleNext}
                disabled={!selectedDates.from || !selectedDates.to || getDuration() > 7}
                className="bg-blue-600 hover:bg-blue-700"
              >
                Next
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default DateSelection;

