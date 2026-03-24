import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface TripPlanningData {
  destination: string;
  startDate: Date | null;
  endDate: Date | null;
  companyType: 'solo' | 'partner' | 'friends' | 'family' | null;
  withPets: boolean | null;
  foodPreference: 'vegetarian' | 'non-vegetarian' | 'both' | null;
  ecoMode: boolean;
  interests: string[];
  budget: number | null;
  emergencyContact?: {
    name: string;
    phone: string;
    relation: string;
  };
  languages?: string[];
  transportPreference?: string;
  itineraryId?: string;
  backendItinerary?: any;
}

interface TripPlanningContextType {
  tripData: TripPlanningData;
  updateTripData: (updates: Partial<TripPlanningData>) => void;
  resetTripData: () => void;
  currentStep: number;
  setCurrentStep: (step: number) => void;
  totalSteps: number;
  goToNextStep: () => void;
  goToPreviousStep: () => void;
}

const initialTripData: TripPlanningData = {
  destination: '',
  startDate: null,
  endDate: null,
  companyType: null,
  withPets: null,
  foodPreference: null,
  ecoMode: false,
  interests: [],
  budget: null,
};

const TripPlanningContext = createContext<TripPlanningContextType | undefined>(undefined);

export const useTripPlanning = () => {
  const context = useContext(TripPlanningContext);
  if (!context) {
    throw new Error('useTripPlanning must be used within a TripPlanningProvider');
  }
  return context;
};

interface TripPlanningProviderProps {
  children: ReactNode;
}

export const TripPlanningProvider: React.FC<TripPlanningProviderProps> = ({ children }) => {
  const [tripData, setTripData] = useState<TripPlanningData>(initialTripData);
  const [currentStep, setCurrentStep] = useState(1);
  const totalSteps = 8;

  const updateTripData = (updates: Partial<TripPlanningData>) => {
    setTripData(prev => ({ ...prev, ...updates }));
  };

  const resetTripData = () => {
    setTripData(initialTripData);
    setCurrentStep(1);
  };

  const goToNextStep = () => {
    setCurrentStep(prev => Math.min(prev + 1, totalSteps));
  };

  const goToPreviousStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
  };

  return (
    <TripPlanningContext.Provider
      value={{
        tripData,
        updateTripData,
        resetTripData,
        currentStep,
        setCurrentStep,
        totalSteps,
        goToNextStep,
        goToPreviousStep,
      }}
    >
      {children}
    </TripPlanningContext.Provider>
  );
};

