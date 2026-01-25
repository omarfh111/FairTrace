import { useState } from "react";
import { Dashboard } from "@/components/Dashboard";
import { FairTraceLoading } from "@/components/loading/FairTraceLoading";

const Index = () => {
  const [isLoading, setIsLoading] = useState(true);

  if (isLoading) {
    return <FairTraceLoading onLoadingComplete={() => setIsLoading(false)} duration={8000} />;
  }

  return <Dashboard />;
};

export default Index;
