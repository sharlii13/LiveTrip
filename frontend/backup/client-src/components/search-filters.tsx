import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import StarRating from "./star-rating";

interface SearchFiltersProps {
  onFiltersChange: (filters: {
    categories: string[];
    rating: number | null;
    priceRanges: string[];
  }) => void;
}

export default function SearchFilters({ onFiltersChange }: SearchFiltersProps) {
  const [categories, setCategories] = useState<string[]>([]);
  const [rating, setRating] = useState<number | null>(null);
  const [priceRanges, setPriceRanges] = useState<string[]>([]);

  const handleCategoryChange = (category: string, checked: boolean) => {
    const newCategories = checked 
      ? [...categories, category]
      : categories.filter(c => c !== category);
    
    setCategories(newCategories);
    onFiltersChange({ categories: newCategories, rating, priceRanges });
  };

  const handleRatingChange = (value: string) => {
    const newRating = value === "none" ? null : parseInt(value);
    setRating(newRating);
    onFiltersChange({ categories, rating: newRating, priceRanges });
  };

  const handlePriceRangeChange = (priceRange: string, checked: boolean) => {
    const newPriceRanges = checked 
      ? [...priceRanges, priceRange]
      : priceRanges.filter(p => p !== priceRange);
    
    setPriceRanges(newPriceRanges);
    onFiltersChange({ categories, rating, priceRanges: newPriceRanges });
  };

  return (
    <Card data-testid="card-search-filters">
      <CardHeader>
        <CardTitle>Filters</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Category Filter */}
        <div>
          <h4 className="font-medium mb-3">Category</h4>
          <div className="space-y-2">
            {[
              { id: "hotel", label: "Hotels" },
              { id: "restaurant", label: "Restaurants" },
              { id: "attraction", label: "Attractions" },
              { id: "experience", label: "Experiences" }
            ].map((category) => (
              <div key={category.id} className="flex items-center space-x-2">
                <Checkbox
                  id={category.id}
                  checked={categories.includes(category.id)}
                  onCheckedChange={(checked) => handleCategoryChange(category.id, checked === true)}
                  data-testid={`checkbox-category-${category.id}`}
                />
                <Label htmlFor={category.id} className="text-sm">
                  {category.label}
                </Label>
              </div>
            ))}
          </div>
        </div>
        
        {/* Rating Filter */}
        <div>
          <h4 className="font-medium mb-3">Rating</h4>
          <RadioGroup value={rating?.toString() || "none"} onValueChange={handleRatingChange}>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="none" id="rating-none" data-testid="radio-rating-none" />
              <Label htmlFor="rating-none" className="text-sm">Any rating</Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="5" id="rating-5" data-testid="radio-rating-5" />
              <Label htmlFor="rating-5" className="flex items-center text-sm">
                <StarRating rating={5} size="sm" className="mr-2" />
                5 stars
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="4" id="rating-4" data-testid="radio-rating-4" />
              <Label htmlFor="rating-4" className="flex items-center text-sm">
                <StarRating rating={4} size="sm" className="mr-2" />
                4+ stars
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="3" id="rating-3" data-testid="radio-rating-3" />
              <Label htmlFor="rating-3" className="flex items-center text-sm">
                <StarRating rating={3} size="sm" className="mr-2" />
                3+ stars
              </Label>
            </div>
          </RadioGroup>
        </div>
        
        {/* Price Range */}
        <div>
          <h4 className="font-medium mb-3">Price Range</h4>
          <div className="space-y-2">
            {[
              { id: "$", label: "$ Budget" },
              { id: "$$", label: "$$ Mid-range" },
              { id: "$$$", label: "$$$ Luxury" }
            ].map((price) => (
              <div key={price.id} className="flex items-center space-x-2">
                <Checkbox
                  id={price.id}
                  checked={priceRanges.includes(price.id)}
                  onCheckedChange={(checked) => handlePriceRangeChange(price.id, checked === true)}
                  data-testid={`checkbox-price-${price.id.replace('$', 'dollar')}`}
                />
                <Label htmlFor={price.id} className="text-sm">
                  {price.label}
                </Label>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
