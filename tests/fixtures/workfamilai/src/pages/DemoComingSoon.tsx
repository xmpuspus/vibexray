
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useNavigate } from 'react-router-dom';
import { 
  Brain, 
  Sparkles, 
  Zap, 
  Users, 
  Target, 
  ArrowLeft, 
  Bell, 
  Calendar,
  CheckCircle,
  Clock,
  Rocket,
  Mail
} from 'lucide-react';
import { Footer } from '@/components/ui/footer';

const DemoComingSoon = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [currentFeature, setCurrentFeature] = useState(0);

  const demoFeatures = [
    "Live AI agent conversations with real-time responses",
    "Interactive family member collaboration scenarios",
    "Real-time neural network activity visualization",
    "Dynamic problem-solving demonstrations",
    "Multi-agent coordination showcases"
  ];

  const milestones = [
    { title: "Core Infrastructure", status: "completed", date: "Q4 2024" },
    { title: "Family Member Integration", status: "completed", date: "Q1 2025" },
    { title: "Neural Network Visualization", status: "completed", date: "Q2 2025" },
    { title: "Live Demo Platform", status: "in-progress", date: "Q3 2025" },
    { title: "Public Beta Launch", status: "upcoming", date: "Q4 2025" }
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentFeature((prev) => (prev + 1) % demoFeatures.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      setIsSubscribed(true);
      setEmail('');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex flex-col">
      {/* Hero Section */}
      <div className="relative overflow-hidden bg-gradient-to-r from-blue-900 via-purple-900 to-indigo-900 text-white">
        {/* Animated background */}
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(6,182,212,0.1)_0%,transparent_70%)] animate-pulse"></div>
          <div className="absolute top-1/4 left-1/4 w-4 h-4 bg-cyan-400 rounded-full opacity-60 animate-ping"></div>
          <div className="absolute top-3/4 right-1/4 w-3 h-3 bg-purple-400 rounded-full opacity-40 animate-ping" style={{ animationDelay: '1s' }}></div>
          <div className="absolute top-1/2 left-3/4 w-2 h-2 bg-blue-400 rounded-full opacity-50 animate-ping" style={{ animationDelay: '2s' }}></div>
        </div>
        
        <div className="absolute inset-0 bg-black opacity-50"></div>
        <div className="relative max-w-7xl mx-auto px-4 py-16 sm:px-6 lg:px-8">
          {/* Back navigation */}
          <div className="mb-8">
            <Button 
              onClick={() => navigate('/')}
              variant="outline" 
              className="border-white/30 text-white hover:bg-white/10 backdrop-blur-sm"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Home
            </Button>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center space-x-3 mb-6">
              <Rocket className="h-12 w-12 text-cyan-400 animate-pulse" />
              <h1 className="text-4xl md:text-6xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
                Live Demo
              </h1>
              <Sparkles className="h-12 w-12 text-purple-400 animate-pulse" style={{ animationDelay: '0.5s' }} />
            </div>
            
            <Badge variant="outline" className="border-yellow-400/50 text-yellow-300 bg-yellow-400/10 backdrop-blur-sm mb-6 px-4 py-2 text-lg">
              <Clock className="mr-2 h-4 w-4" />
              Coming Soon • Q4 2025
            </Badge>

            <p className="text-xl md:text-2xl mb-8 text-gray-200 max-w-4xl mx-auto">
              Experience the workfamilyai Family in action with live, interactive demonstrations 
              of our AI agents collaborating in real-time to solve complex challenges.
            </p>

            {/* Dynamic feature showcase */}
            <div className="mb-8 h-16 flex items-center justify-center">
              <div className="flex items-center space-x-3 bg-blue-500/20 backdrop-blur-md rounded-full px-6 py-3 border border-blue-400/30">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-blue-200 text-sm font-medium">
                  Preview: {demoFeatures[currentFeature]}
                </span>
                <Zap className="h-4 w-4 text-yellow-400 animate-pulse" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Email Signup Section */}
      <div className="max-w-4xl mx-auto px-4 py-16 sm:px-6 lg:px-8">
        <Card className="bg-white/70 backdrop-blur-md border-0 shadow-2xl">
          <CardHeader className="text-center">
            <CardTitle className="text-3xl font-bold text-gray-900 mb-4">
              Get Early Access
            </CardTitle>
            <p className="text-lg text-gray-600">
              Be the first to experience the live demo when it launches. Join our exclusive preview list.
            </p>
          </CardHeader>
          <CardContent>
            {!isSubscribed ? (
              <form onSubmit={handleEmailSubmit} className="flex flex-col sm:flex-row gap-4 max-w-md mx-auto">
                <Input
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="flex-1"
                />
                <Button type="submit" className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700">
                  <Bell className="mr-2 h-4 w-4" />
                  Notify Me
                </Button>
              </form>
            ) : (
              <div className="text-center">
                <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
                <p className="text-lg font-semibold text-green-600">You're on the list!</p>
                <p className="text-gray-600">We'll notify you as soon as the live demo is ready.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Development Timeline */}
      <div className="max-w-6xl mx-auto px-4 py-16 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Development Timeline</h2>
          <p className="text-lg text-gray-600">
            Track our progress as we build the most advanced AI family demonstration platform.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
          {milestones.map((milestone, index) => (
            <Card key={index} className={`relative ${
              milestone.status === 'completed' ? 'bg-green-50 border-green-200' :
              milestone.status === 'in-progress' ? 'bg-blue-50 border-blue-200' :
              'bg-gray-50 border-gray-200'
            }`}>
              <CardContent className="p-6 text-center">
                <div className={`w-12 h-12 rounded-full mx-auto mb-4 flex items-center justify-center ${
                  milestone.status === 'completed' ? 'bg-green-500' :
                  milestone.status === 'in-progress' ? 'bg-blue-500' :
                  'bg-gray-400'
                }`}>
                  {milestone.status === 'completed' ? (
                    <CheckCircle className="h-6 w-6 text-white" />
                  ) : milestone.status === 'in-progress' ? (
                    <Clock className="h-6 w-6 text-white animate-pulse" />
                  ) : (
                    <Calendar className="h-6 w-6 text-white" />
                  )}
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{milestone.title}</h3>
                <p className="text-sm text-gray-600">{milestone.date}</p>
                <Badge 
                  variant="outline" 
                  className={`mt-2 ${
                    milestone.status === 'completed' ? 'border-green-500 text-green-700' :
                    milestone.status === 'in-progress' ? 'border-blue-500 text-blue-700' :
                    'border-gray-500 text-gray-700'
                  }`}
                >
                  {milestone.status === 'completed' ? 'Complete' :
                   milestone.status === 'in-progress' ? 'In Progress' : 'Upcoming'}
                </Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* What's Available Now */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="max-w-6xl mx-auto px-4 py-16 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Explore What's Available Now</h2>
            <p className="text-lg text-gray-600">
              While you wait for the live demo, discover the workfamilyai Family and their capabilities.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <Card className="hover:scale-105 transition-transform duration-300 cursor-pointer" onClick={() => navigate('/')}>
              <CardContent className="p-6 text-center">
                <Brain className="h-12 w-12 text-blue-500 mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">Neural Network</h3>
                <p className="text-gray-600 mb-4">Explore the family's interconnected intelligence and capabilities.</p>
                <Button variant="outline">View Network</Button>
              </CardContent>
            </Card>

            <Card className="hover:scale-105 transition-transform duration-300 cursor-pointer" onClick={() => navigate('/scenarios')}>
              <CardContent className="p-6 text-center">
                <Target className="h-12 w-12 text-green-500 mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">Business Scenarios</h3>
                <p className="text-gray-600 mb-4">See how the family handles real-world business challenges.</p>
                <Button variant="outline">View Scenarios</Button>
              </CardContent>
            </Card>

            <Card className="hover:scale-105 transition-transform duration-300 cursor-pointer" onClick={() => navigate('/holo-org')}>
              <CardContent className="p-6 text-center">
                <Users className="h-12 w-12 text-purple-500 mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">Holo-Org Dashboard</h3>
                <p className="text-gray-600 mb-4">Experience the organizational intelligence in action.</p>
                <Button variant="outline">View Dashboard</Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
};

export default DemoComingSoon;
