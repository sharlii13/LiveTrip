import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Heart, 
  Users, 
  Lightbulb, 
  Target, 
  ArrowLeft,
  Globe,
  Zap,
  Shield,
  Star,
  CheckCircle
} from 'lucide-react';
import LiveTripLogo from '@/components/LiveTripLogo';

const About: React.FC = () => {
  const navigate = useNavigate();

  const handleGoBack = () => {
    navigate('/');
  };

  const values = [
    {
      icon: Zap,
      title: 'Flexibility',
      description: 'Replace rigid plans with dynamic, real-time itineraries that adapt to your journey.'
    },
    {
      icon: Globe,
      title: 'Simplicity',
      description: 'Bring weather, traffic, events, and schedules into one seamless platform.'
    },
    {
      icon: Heart,
      title: 'Personalization',
      description: 'Tailor every journey to your mood, preferences, and spontaneity.'
    }
  ];

  const features = [
    'Real-time itinerary updates',
    'Weather-aware planning',
    'Traffic optimization',
    'Local event integration',
    'Personalized recommendations',
    'Seamless app experience'
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 via-white to-brand-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button variant="outline" onClick={handleGoBack}>
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Home
              </Button>
              <div>
                <h1 className="text-3xl font-bold text-gray-800">About Us</h1>
                <p className="text-gray-600">Learn more about The Living Itinerary</p>
              </div>
            </div>
            <LiveTripLogo size="lg" />
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-12">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <div className="mb-8">
            <h2 className="text-4xl font-bold text-gray-800 mb-6">
              Welcome to The Living Itinerary
            </h2>
            <p className="text-xl text-gray-600 max-w-4xl mx-auto leading-relaxed">
              At The Living Itinerary, we believe travel should be as joyful and stress-free as the memories you create. 
              Too often, trips are weighed down by rigid plans, endless app juggling, and the frustration of last-minute surprises. 
              We set out to change that.
            </p>
          </div>
        </div>

        {/* Mission Statement */}
        <Card className="mb-16 bg-gradient-to-r from-brand-600 to-brand-600 text-white">
          <CardContent className="p-12">
            <div className="text-center">
              <h3 className="text-3xl font-bold mb-6">Our Mission</h3>
              <p className="text-xl leading-relaxed max-w-4xl mx-auto">
                Our platform is designed to be your smart travel companion — one that adapts in real time, 
                learns your preferences, and keeps your journey smooth no matter what comes your way. 
                Whether it's a sudden change in weather, unexpected traffic, or a new event worth exploring, 
                The Living Itinerary evolves with you, so your plans never hold you back.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Team Section */}
        <div className="mb-16">
          <div className="text-center mb-12">
            <h3 className="text-3xl font-bold text-gray-800 mb-4">Our Team</h3>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              We are a passionate team of innovators, travelers, and problem-solvers who understand 
              the challenges of planning and experiencing trips.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <Card className="text-center p-6 hover:shadow-lg transition-shadow">
              <CardContent>
                <Users className="w-16 h-16 text-brand-700 mx-auto mb-4" />
                <h4 className="text-xl font-semibold text-gray-800 mb-2">Innovators</h4>
                <p className="text-gray-600">
                  Creative minds pushing the boundaries of travel technology
                </p>
              </CardContent>
            </Card>
            
            <Card className="text-center p-6 hover:shadow-lg transition-shadow">
              <CardContent>
                <Globe className="w-16 h-16 text-brand-700 mx-auto mb-4" />
                <h4 className="text-xl font-semibold text-gray-800 mb-2">Travelers</h4>
                <p className="text-gray-600">
                  Experienced adventurers who understand the real needs of travelers
                </p>
              </CardContent>
            </Card>
            
            <Card className="text-center p-6 hover:shadow-lg transition-shadow">
              <CardContent>
                <Lightbulb className="w-16 h-16 text-brand-700 mx-auto mb-4" />
                <h4 className="text-xl font-semibold text-gray-800 mb-2">Problem-Solvers</h4>
                <p className="text-gray-600">
                  Dedicated to solving the everyday challenges of travel planning
                </p>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Core Values */}
        <div className="mb-16">
          <div className="text-center mb-12">
            <h3 className="text-3xl font-bold text-gray-800 mb-4">Our Core Values</h3>
            <p className="text-xl text-gray-600">
              Our mission is simple but powerful
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {values.map((value, index) => (
              <Card key={index} className="p-8 hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
                <CardContent className="text-center">
                  <div className="w-16 h-16 bg-gradient-to-r from-brand-500 to-brand-500 rounded-full flex items-center justify-center mx-auto mb-6">
                    <value.icon className="w-8 h-8 text-white" />
                  </div>
                  <h4 className="text-2xl font-bold text-gray-800 mb-4">{value.title}</h4>
                  <p className="text-gray-600 leading-relaxed">{value.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Features */}
        <div className="mb-16">
          <Card className="bg-gradient-to-r from-brand-50 to-brand-50 border-brand-200">
            <CardHeader className="text-center">
              <CardTitle className="text-3xl font-bold text-gray-800 mb-4">What We Offer</CardTitle>
              <CardDescription className="text-xl text-gray-600">
                At the heart of our work is the belief that technology should empower exploration, not complicate it.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-8">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {features.map((feature, index) => (
                  <div key={index} className="flex items-center space-x-3 p-3 rounded-lg bg-white/50">
                    <CheckCircle className="w-5 h-5 text-brand-700 flex-shrink-0" />
                    <span className="text-gray-700 font-medium">{feature}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Philosophy */}
        <div className="text-center">
          <Card className="bg-gradient-to-r from-brand-600 to-brand-600 text-white">
            <CardContent className="p-12">
              <Star className="w-16 h-16 mx-auto mb-6 text-yellow-300" />
              <h3 className="text-3xl font-bold mb-6">Our Philosophy</h3>
              <p className="text-xl leading-relaxed max-w-4xl mx-auto">
                At the heart of our work is the belief that technology should empower exploration, not complicate it. 
                With The Living Itinerary, you don't just plan trips — you live them.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Call to Action */}
        <div className="text-center mt-16">
          <h3 className="text-2xl font-bold text-gray-800 mb-4">Ready to Experience The Living Itinerary?</h3>
          <p className="text-gray-600 mb-8">Start planning your next adventure with us today.</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button 
              onClick={() => navigate('/search')}
              className="bg-brand-700 hover:bg-brand-800 text-white px-8 py-3"
            >
              Start Planning
            </Button>
            <Button 
              onClick={() => navigate('/itinerary')}
              variant="outline"
              className="px-8 py-3"
            >
              View Sample Itinerary
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default About;
