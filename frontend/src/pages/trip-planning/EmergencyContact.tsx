import { useState } from "react";
import { useTripPlanning } from "@/contexts/TripPlanningContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Phone, User, AlertTriangle, Shield, ChevronLeft, ChevronRight } from "lucide-react";
import ProgressIndicator from "@/components/ProgressIndicator";

export default function EmergencyContact() {
  const { tripData, updateTripData, goToPreviousStep, goToNextStep } = useTripPlanning();
  const [emergencyName, setEmergencyName] = useState(tripData.emergencyContact?.name || "");
  const [emergencyPhone, setEmergencyPhone] = useState(tripData.emergencyContact?.phone || "");
  const [emergencyRelation, setEmergencyRelation] = useState(tripData.emergencyContact?.relation || "");
  const [isValid, setIsValid] = useState(false);

  const validateForm = () => {
    const valid = emergencyName.trim() !== "" && emergencyPhone.trim() !== "" && emergencyRelation.trim() !== "";
    setIsValid(valid);
  };

  const handleNext = () => {
    if (isValid) {
      updateTripData({
        emergencyContact: {
          name: emergencyName.trim(),
          phone: emergencyPhone.trim(),
          relation: emergencyRelation.trim()
        }
      });
      goToNextStep();
    }
  };

  const handlePrevious = () => {
    updateTripData({
      emergencyContact: {
        name: emergencyName.trim(),
        phone: emergencyPhone.trim(),
        relation: emergencyRelation.trim()
      }
    });
    goToPreviousStep();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 to-brand-100 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <ProgressIndicator currentStep={6} totalSteps={8} tripName="Trip Planning" />
        
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-4">Emergency Contact Information</h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Please provide emergency contact details for your safety during the trip
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Form */}
          <div className="lg:col-span-2">
            <Card className="shadow-lg">
              <CardHeader>
                <CardTitle className="text-brand-800 flex items-center">
                  <Shield className="w-6 h-6 mr-2" />
                  Emergency Contact Details
                </CardTitle>
                <CardDescription>
                  This information will be used only in case of emergency during your trip
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Emergency Contact Name */}
                <div>
                  <Label htmlFor="emergencyName" className="text-base font-medium">
                    Emergency Contact Name *
                  </Label>
                  <div className="relative mt-2">
                    <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <Input
                      id="emergencyName"
                      type="text"
                      placeholder="Enter full name"
                      value={emergencyName}
                      onChange={(e) => {
                        setEmergencyName(e.target.value);
                        validateForm();
                      }}
                      className="pl-10 border-brand-300 focus:border-brand-500 focus:ring-brand-500"
                    />
                  </div>
                </div>

                {/* Emergency Contact Phone */}
                <div>
                  <Label htmlFor="emergencyPhone" className="text-base font-medium">
                    Emergency Contact Phone Number *
                  </Label>
                  <div className="relative mt-2">
                    <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <Input
                      id="emergencyPhone"
                      type="tel"
                      placeholder="+1 (555) 123-4567"
                      value={emergencyPhone}
                      onChange={(e) => {
                        setEmergencyPhone(e.target.value);
                        validateForm();
                      }}
                      className="pl-10 border-brand-300 focus:border-brand-500 focus:ring-brand-500"
                    />
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    Include country code for international numbers
                  </p>
                </div>

                {/* Relationship */}
                <div>
                  <Label htmlFor="emergencyRelation" className="text-base font-medium">
                    Relationship *
                  </Label>
                  <div className="mt-2">
                    <Input
                      id="emergencyRelation"
                      type="text"
                      placeholder="e.g., Spouse, Parent, Sibling, Friend"
                      value={emergencyRelation}
                      onChange={(e) => {
                        setEmergencyRelation(e.target.value);
                        validateForm();
                      }}
                      className="border-brand-300 focus:border-brand-500 focus:ring-brand-500"
                    />
                  </div>
                </div>

                {/* Navigation Buttons */}
                <div className="flex justify-between pt-6">
                  <Button
                    onClick={handlePrevious}
                    variant="outline"
                    className="flex items-center px-6 py-2"
                  >
                    <ChevronLeft className="w-4 h-4 mr-2" />
                    Previous
                  </Button>
                  
                  <Button
                    onClick={handleNext}
                    disabled={!isValid}
                    className="bg-brand-700 hover:bg-brand-800 flex items-center px-6 py-2"
                  >
                    Next
                    <ChevronRight className="w-4 h-4 ml-2" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Trip Summary */}
            <Card className="bg-gradient-to-br from-brand-50 to-brand-50 border-brand-200">
              <CardHeader>
                <CardTitle className="text-brand-800 text-lg">Trip Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Destination:</span>
                  <Badge className="bg-brand-100 text-brand-800">
                    {tripData.destination || "Not selected"}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Dates:</span>
                  <span className="text-sm text-gray-600">
                    {tripData.startDate ? new Date(tripData.startDate).toLocaleDateString() : "Not set"} - 
                    {tripData.endDate ? new Date(tripData.endDate).toLocaleDateString() : "Not set"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Company:</span>
                  <span className="text-sm text-gray-600">{tripData.companyType || "Not selected"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Food:</span>
                  <span className="text-sm text-gray-600">{tripData.foodPreference || "Not selected"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Eco Mode:</span>
                  <span className="text-sm text-gray-600">{tripData.ecoMode ? "Enabled" : "Disabled"}</span>
                </div>
              </CardContent>
            </Card>

            {/* Safety Tips */}
            <Card className="bg-gradient-to-br from-red-50 to-orange-50 border-red-200">
              <CardHeader>
                <CardTitle className="text-red-800 text-lg flex items-center">
                  <AlertTriangle className="w-5 h-5 mr-2" />
                  Safety Tips
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="text-sm text-gray-700">
                  <p className="font-medium mb-2">Emergency Contact Guidelines:</p>
                  <ul className="space-y-1 text-xs">
                    <li>• Choose someone who can be reached 24/7</li>
                    <li>• Ensure they know about your travel plans</li>
                    <li>• Provide them with your itinerary details</li>
                    <li>• Keep their contact info easily accessible</li>
                    <li>• Consider local emergency services too</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}


