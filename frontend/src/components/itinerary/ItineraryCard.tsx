import { memo } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { motion } from "framer-motion";

export type ItineraryBadge = "indoor" | "traffic" | "replanned";

export type ItineraryItemProps = {
  startTime: string;
  endTime: string;
  name: string;
  categoryTag: string; // e.g., temple, museum, restaurant
  durationText: string; // e.g., ~2h activity + buffer
  badges?: ItineraryBadge[];
};

function badgeLabel(b: ItineraryBadge) {
  switch (b) {
    case "indoor":
      return "☔ indoor";
    case "traffic":
      return "🚗 traffic delay";
    case "replanned":
      return "⚡ replanned";
    default:
      return b;
  }
}

function tagEmoji(tag: string) {
  const t = tag.toLowerCase();
  if (t.includes("temple")) return "⛩️";
  if (t.includes("museum")) return "🏛️";
  if (t.includes("restaurant") || t.includes("food")) return "🍽️";
  if (t.includes("park") || t.includes("garden")) return "🌳";
  if (t.includes("shopping")) return "🛍️";
  return "📍";
}

export const ItineraryCard = memo(function ItineraryCard(props: ItineraryItemProps) {
  const { startTime, endTime, name, categoryTag, durationText, badges } = props;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
    >
      <Card className="border rounded-2xl shadow-sm hover:shadow-md transition-all bg-white">
        <CardContent className="p-5 flex items-start gap-5">
          {/* Time column */}
          <div className="flex flex-col items-center shrink-0 w-28">
            <div className="text-sm font-semibold text-brand-700 whitespace-nowrap">{startTime || ""}</div>
            <div className="text-[10px] text-muted-foreground my-0.5">to</div>
            <div className="text-sm font-semibold text-brand-700 whitespace-nowrap">{endTime || ""}</div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <div className="text-lg" aria-hidden>{tagEmoji(categoryTag)}</div>
              <div className="font-semibold truncate" title={name}>{name}</div>
              <span className="ml-auto" />
              <Badge className="capitalize bg-brand-100 text-brand-800 hover:bg-brand-100">{categoryTag}</Badge>
            </div>
            <div className="text-xs text-muted-foreground mt-1">{durationText}</div>

            {badges && badges.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {badges.map((b) => (
                  <Badge key={b} variant="outline" className="text-[11px]">
                    {badgeLabel(b)}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
});
