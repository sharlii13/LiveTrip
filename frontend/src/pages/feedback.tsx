import { useState } from "react";
import { Star, Send, MessageSquare, ThumbsUp, ThumbsDown, Bug, Lightbulb, Heart } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import PageHero from "@/components/PageHero";

export default function FeedbackPage() {
  const { user, isAuthenticated } = useAuth();
  const [feedbackType, setFeedbackType] = useState("general");
  const [rating, setRating] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [email, setEmail] = useState(user?.email || "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const feedbackTypes = [
    { value: "general", label: "General Feedback", icon: MessageSquare, description: "Share your overall experience" },
    { value: "bug", label: "Bug Report", icon: Bug, description: "Report technical issues" },
    { value: "feature", label: "Feature Request", icon: Lightbulb, description: "Suggest new features" },
    { value: "compliment", label: "Compliment", icon: Heart, description: "Share what you love" }
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // In a real app, you would send this to your backend
      console.log("Feedback submitted:", {
        type: feedbackType,
        rating,
        feedback,
        email,
        user: user?.id
      });

      setIsSubmitted(true);
      setFeedback("");
      setRating(0);
    } catch (error) {
      console.error("Error submitting feedback:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-brand-50 to-brand-100 py-12">
        <div className="max-w-2xl mx-auto px-4">
          <Card className="text-center">
            <CardHeader>
              <div className="mx-auto w-16 h-16 bg-brand-100 rounded-full flex items-center justify-center mb-4">
                <ThumbsUp className="w-8 h-8 text-brand-700" />
              </div>
              <CardTitle className="text-2xl text-brand-800">Thank You!</CardTitle>
              <CardDescription className="text-lg">
                Your feedback has been submitted successfully. We appreciate your input!
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button 
                onClick={() => setIsSubmitted(false)}
                className="bg-brand-700 hover:bg-brand-800"
              >
                Submit Another Feedback
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <>
    <PageHero title="Share your feedback" clip="food" icon={<MessageSquare className="w-6 h-6" />}
              subtitle="Help us improve LiveTrip: share your thoughts, report issues or suggest new features." />
    <div className="min-h-screen bg-gradient-to-br from-brand-50 to-brand-100 py-12">
      <div className="max-w-4xl mx-auto px-4">

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Feedback Types */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <MessageSquare className="w-5 h-5 mr-2" />
                  Feedback Type
                </CardTitle>
                <CardDescription>
                  Choose the type of feedback you'd like to share
                </CardDescription>
              </CardHeader>
              <CardContent>
                <RadioGroup value={feedbackType} onValueChange={setFeedbackType}>
                  {feedbackTypes.map((type) => {
                    const IconComponent = type.icon;
                    return (
                      <div key={type.value} className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                        <RadioGroupItem value={type.value} id={type.value} />
                        <div className="flex-1">
                          <div className="flex items-center">
                            <IconComponent className="w-4 h-4 mr-2 text-brand-700" />
                            <Label htmlFor={type.value} className="font-medium cursor-pointer">
                              {type.label}
                            </Label>
                          </div>
                          <p className="text-sm text-gray-500 mt-1">{type.description}</p>
                        </div>
                      </div>
                    );
                  })}
                </RadioGroup>
              </CardContent>
            </Card>
          </div>

          {/* Feedback Form */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>Your Feedback</CardTitle>
                <CardDescription>
                  {feedbackTypes.find(t => t.value === feedbackType)?.description}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                  {/* Rating */}
                  <div>
                    <Label className="text-base font-medium">How would you rate your experience?</Label>
                    <div className="flex items-center space-x-2 mt-2">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          type="button"
                          onClick={() => setRating(star)}
                          className={`transition-colors ${
                            star <= rating ? 'text-yellow-400' : 'text-gray-300'
                          } hover:text-yellow-400`}
                        >
                          <Star className="w-6 h-6 fill-current" />
                        </button>
                      ))}
                      <span className="ml-2 text-sm text-gray-600">
                        {rating === 0 ? 'No rating' : `${rating} star${rating > 1 ? 's' : ''}`}
                      </span>
                    </div>
                  </div>

                  {/* Feedback Text */}
                  <div>
                    <Label htmlFor="feedback" className="text-base font-medium">
                      Tell us more about your experience
                    </Label>
                    <Textarea
                      id="feedback"
                      placeholder="Share your thoughts, suggestions, or report any issues you encountered..."
                      value={feedback}
                      onChange={(e) => setFeedback(e.target.value)}
                      className="mt-2 min-h-[120px]"
                      required
                    />
                  </div>

                  {/* Email */}
                  <div>
                    <Label htmlFor="email" className="text-base font-medium">
                      Email (optional)
                    </Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="your@email.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="mt-2"
                    />
                    <p className="text-sm text-gray-500 mt-1">
                      We'll only use this to follow up if needed
                    </p>
                  </div>

                  {/* Submit Button */}
                  <Button
                    type="submit"
                    disabled={isSubmitting || !feedback.trim()}
                    className="w-full bg-brand-700 hover:bg-brand-800"
                  >
                    {isSubmitting ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                        Submitting...
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4 mr-2" />
                        Submit Feedback
                      </>
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Additional Info */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="text-center">
            <CardContent className="pt-6">
              <div className="w-12 h-12 bg-brand-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <MessageSquare className="w-6 h-6 text-brand-700" />
              </div>
              <h3 className="font-semibold mb-2">We Listen</h3>
              <p className="text-sm text-gray-600">
                Every piece of feedback is carefully reviewed by our team
              </p>
            </CardContent>
          </Card>

          <Card className="text-center">
            <CardContent className="pt-6">
              <div className="w-12 h-12 bg-brand-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <ThumbsUp className="w-6 h-6 text-brand-700" />
              </div>
              <h3 className="font-semibold mb-2">We Act</h3>
              <p className="text-sm text-gray-600">
                Your suggestions help shape our product roadmap
              </p>
            </CardContent>
          </Card>

          <Card className="text-center">
            <CardContent className="pt-6">
              <div className="w-12 h-12 bg-brand-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Heart className="w-6 h-6 text-brand-700" />
              </div>
              <h3 className="font-semibold mb-2">We Care</h3>
              <p className="text-sm text-gray-600">
                Your experience matters to us and drives our improvements
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
    </>
  );
}


