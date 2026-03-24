import { useState } from "react";
import { useTripPlanning } from "@/contexts/TripPlanningContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Search, Globe, ChevronLeft, ChevronRight, Check } from "lucide-react";
import ProgressIndicator from "@/components/ProgressIndicator";

export default function LanguagePreference() {
  const { tripData, updateTripData, goToPreviousStep, goToNextStep } = useTripPlanning();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(tripData.languages || []);
  const [isValid, setIsValid] = useState(selectedLanguages.length > 0);

  const languages = [
    { code: "en", name: "English", native: "English", flag: "🇺🇸" },
    { code: "es", name: "Spanish", native: "Español", flag: "🇪🇸" },
    { code: "fr", name: "French", native: "Français", flag: "🇫🇷" },
    { code: "de", name: "German", native: "Deutsch", flag: "🇩🇪" },
    { code: "it", name: "Italian", native: "Italiano", flag: "🇮🇹" },
    { code: "pt", name: "Portuguese", native: "Português", flag: "🇵🇹" },
    { code: "ru", name: "Russian", native: "Русский", flag: "🇷🇺" },
    { code: "ja", name: "Japanese", native: "日本語", flag: "🇯🇵" },
    { code: "ko", name: "Korean", native: "한국어", flag: "🇰🇷" },
    { code: "zh", name: "Chinese", native: "中文", flag: "🇨🇳" },
    { code: "ar", name: "Arabic", native: "العربية", flag: "🇸🇦" },
    { code: "hi", name: "Hindi", native: "हिन्दी", flag: "🇮🇳" },
    { code: "th", name: "Thai", native: "ไทย", flag: "🇹🇭" },
    { code: "vi", name: "Vietnamese", native: "Tiếng Việt", flag: "🇻🇳" },
    { code: "tr", name: "Turkish", native: "Türkçe", flag: "🇹🇷" },
    { code: "pl", name: "Polish", native: "Polski", flag: "🇵🇱" },
    { code: "nl", name: "Dutch", native: "Nederlands", flag: "🇳🇱" },
    { code: "sv", name: "Swedish", native: "Svenska", flag: "🇸🇪" },
    { code: "no", name: "Norwegian", native: "Norsk", flag: "🇳🇴" },
    { code: "da", name: "Danish", native: "Dansk", flag: "🇩🇰" },
    { code: "fi", name: "Finnish", native: "Suomi", flag: "🇫🇮" },
    { code: "el", name: "Greek", native: "Ελληνικά", flag: "🇬🇷" },
    { code: "he", name: "Hebrew", native: "עברית", flag: "🇮🇱" },
    { code: "cs", name: "Czech", native: "Čeština", flag: "🇨🇿" },
    { code: "hu", name: "Hungarian", native: "Magyar", flag: "🇭🇺" },
    { code: "ro", name: "Romanian", native: "Română", flag: "🇷🇴" },
    { code: "bg", name: "Bulgarian", native: "Български", flag: "🇧🇬" },
    { code: "hr", name: "Croatian", native: "Hrvatski", flag: "🇭🇷" },
    { code: "sk", name: "Slovak", native: "Slovenčina", flag: "🇸🇰" },
    { code: "sl", name: "Slovenian", native: "Slovenščina", flag: "🇸🇮" }
  ];

  const filteredLanguages = languages.filter(lang =>
    lang.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    lang.native.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleLanguage = (languageCode: string) => {
    const newSelection = selectedLanguages.includes(languageCode)
      ? selectedLanguages.filter(lang => lang !== languageCode)
      : [...selectedLanguages, languageCode];
    
    setSelectedLanguages(newSelection);
    setIsValid(newSelection.length > 0);
  };

  const handleNext = () => {
    if (isValid) {
      updateTripData({ languages: selectedLanguages });
      goToNextStep();
    }
  };

  const handlePrevious = () => {
    updateTripData({ languages: selectedLanguages });
    goToPreviousStep();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <ProgressIndicator currentStep={7} totalSteps={8} tripName="Trip Planning" />
        
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-4">Language Preferences</h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Select the languages you're comfortable with for your trip planning and communication
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Form */}
          <div className="lg:col-span-2">
            <Card className="shadow-lg">
              <CardHeader>
                <CardTitle className="text-blue-800 flex items-center">
                  <Globe className="w-6 h-6 mr-2" />
                  Select Languages
                </CardTitle>
                <CardDescription>
                  Choose all languages you can speak or understand. This helps us provide better recommendations.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Search Bar */}
                <div>
                  <Label htmlFor="languageSearch" className="text-base font-medium">
                    Search Languages
                  </Label>
                  <div className="relative mt-2">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <Input
                      id="languageSearch"
                      type="text"
                      placeholder="Search for languages..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10 border-blue-300 focus:border-blue-500 focus:ring-blue-500"
                    />
                  </div>
                </div>

                {/* Language Selection */}
                <div>
                  <Label className="text-base font-medium mb-3 block">
                    Available Languages ({filteredLanguages.length})
                  </Label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-96 overflow-y-auto border border-gray-200 rounded-lg p-4">
                    {filteredLanguages.map((language) => {
                      const isSelected = selectedLanguages.includes(language.code);
                      return (
                        <div
                          key={language.code}
                          onClick={() => toggleLanguage(language.code)}
                          className={`flex items-center justify-between p-3 rounded-lg border-2 cursor-pointer transition-all duration-200 ${
                            isSelected
                              ? "border-blue-500 bg-blue-50 text-blue-800"
                              : "border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-25"
                          }`}
                        >
                          <div className="flex items-center space-x-3">
                            <span className="text-2xl">{language.flag}</span>
                            <div>
                              <div className="font-medium">{language.name}</div>
                              <div className="text-sm text-gray-500">{language.native}</div>
                            </div>
                          </div>
                          {isSelected && (
                            <Check className="w-5 h-5 text-blue-600" />
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Selected Languages */}
                {selectedLanguages.length > 0 && (
                  <div>
                    <Label className="text-base font-medium mb-3 block">
                      Selected Languages ({selectedLanguages.length})
                    </Label>
                    <div className="flex flex-wrap gap-2">
                      {selectedLanguages.map((langCode) => {
                        const language = languages.find(lang => lang.code === langCode);
                        return (
                          <Badge
                            key={langCode}
                            className="bg-blue-100 text-blue-800 px-3 py-1 text-sm"
                          >
                            {language?.flag} {language?.name}
                          </Badge>
                        );
                      })}
                    </div>
                  </div>
                )}

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
                    className="bg-blue-600 hover:bg-blue-700 flex items-center px-6 py-2"
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
            <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
              <CardHeader>
                <CardTitle className="text-blue-800 text-lg">Trip Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Destination:</span>
                  <Badge className="bg-blue-100 text-blue-800">
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
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Emergency Contact:</span>
                  <span className="text-sm text-gray-600">
                    {tripData.emergencyContact?.name ? "✓ Set" : "Not set"}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Language Tips */}
            <Card className="bg-gradient-to-br from-green-50 to-emerald-50 border-green-200">
              <CardHeader>
                <CardTitle className="text-green-800 text-lg flex items-center">
                  <Globe className="w-5 h-5 mr-2" />
                  Language Tips
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="text-sm text-gray-700">
                  <p className="font-medium mb-2">Why Language Preferences Matter:</p>
                  <ul className="space-y-1 text-xs">
                    <li>• Better local recommendations</li>
                    <li>• Language-specific content</li>
                    <li>• Cultural insights and tips</li>
                    <li>• Emergency communication</li>
                    <li>• Local business interactions</li>
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


