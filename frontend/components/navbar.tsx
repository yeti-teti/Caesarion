"use client";

import { Button } from "./ui/button";
import { VercelIcon } from "./icons";
import Link from "next/link";

export const Navbar = () => {
  return (
    <div className="p-2 flex flex-row gap-2 justify-between">
            
      <Button>
        Connected
      </Button>

    </div>
  );
};
