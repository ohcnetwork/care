import { ReactNode, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface FeatureWrapperProps {
  children: ReactNode;
  locked?: boolean;
  title?: string;
}

export default function FeatureWrapper({
  children,
  locked = false,
  title = "Upgrade to Parxio Pro (Rs 4,000/mo) to unlock Hospital Management.",
}: FeatureWrapperProps) {
  const [open, setOpen] = useState(false);

  if (!locked) {
    return <>{children}</>;
  }

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            setOpen(true);
          }
        }}
        className="w-full text-left cursor-pointer"
      >
        <div className="pointer-events-none blur-[1.2px] opacity-75">{children}</div>
      </div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upgrade to Parxio Pro</DialogTitle>
            <DialogDescription>{title}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={() => setOpen(false)}>Maybe Later</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
