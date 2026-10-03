import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, Sparkles, Zap, Rocket, Crown } from "lucide-react";
import { useErrorHandler } from '@/hooks/useErrorHandler';
import { invokeEdgeFunction, getCurrentUser } from '@/lib/supabaseHelpers';
import type { IconProps } from '@/types/shared';

interface CreditPackage {
  id: string;
  name: string;
  credits: number;
  price: number;
  priceId: string;
  popular?: boolean;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
}

const creditPackages: CreditPackage[] = [
  {
    id: "starter",
    name: "Starter",
    credits: 1000,
    price: 10,
    priceId: "price_1SIsUMBu3m83VcDA5X8MPfrS",
    icon: Sparkles,
    description: "Perfect pentru testare",
  },
  {
    id: "pro",
    name: "Professional",
    credits: 2500,
    price: 20,
    priceId: "price_1SIsUPBu3m83VcDAqCC955qF",
    popular: true,
    icon: Zap,
    description: "Cel mai popular",
  },
  {
    id: "business",
    name: "Business",
    credits: 5000,
    price: 40,
    priceId: "price_1SIsUQBu3m83VcDAQUwk4CZZ",
    icon: Rocket,
    description: "Pentru utilizare intensă",
  },
  {
    id: "enterprise",
    name: "Enterprise",
    credits: 10000,
    price: 70,
    priceId: "price_1SIsUQBu3m83VcDAykzaXTeT",
    icon: Crown,
    description: "Soluție completă",
  },
];

export const AICreditsPurchase = () => {
  const [loading, setLoading] = useState<string | null>(null);

  const { handleError, handleSuccess } = useErrorHandler();

  const handlePurchase = async (priceId: string, packageId: string) => {
    setLoading(packageId);
    try {
      await getCurrentUser();

      const data = await invokeEdgeFunction<any, { url?: string }>("create-credits-checkout", {
        priceId,
      });

      if (data?.url) {
        window.location.href = data.url;
      }
    } catch (error) {
      handleError(error, 'crearea checkout-ului');
    } finally {
