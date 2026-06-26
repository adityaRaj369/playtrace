import { useEffect, useState } from "react";

// Load an image element from a URL; returns the HTMLImageElement once ready.
export function useImage(src) {
  const [img, setImg] = useState(null);
  useEffect(() => {
    if (!src) return;
    let cancelled = false;
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => !cancelled && setImg(image);
    image.onerror = () => !cancelled && setImg(null);
    image.src = src;
    return () => {
      cancelled = true;
    };
  }, [src]);
  return img;
}
