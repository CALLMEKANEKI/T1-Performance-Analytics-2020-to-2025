import { useEffect, useState } from "react";
import clsx from "clsx";
import { getChampionImageUrl } from "../lib/api";

export default function ChampionAvatar({
  imageUrl,
  championName = "",
  size = 40,
  className = "",
}) {
  const fallbackUrl = championName ? getChampionImageUrl(championName) : null;
  const [source, setSource] = useState(imageUrl || fallbackUrl);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setSource(imageUrl || fallbackUrl);
    setFailed(false);
  }, [imageUrl, fallbackUrl]);

  function handleImageError() {
    if (imageUrl && source === imageUrl && fallbackUrl && fallbackUrl !== imageUrl) {
      setSource(fallbackUrl);
      return;
    }
    setFailed(true);
  }

  return (
    <span
      className={clsx(
        "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-surfaceAlt font-semibold uppercase text-textMuted",
        className
      )}
      style={{ width: size, height: size, minWidth: size, minHeight: size }}
      role="img"
      aria-label={championName ? `${championName} champion icon` : "Champion icon"}
    >
      {source && !failed ? (
        <img
          src={source}
          alt=""
          width={size}
          height={size}
          loading="lazy"
          className="h-full w-full object-cover"
          onError={handleImageError}
        />
      ) : (
        <span className="text-sm">{championName.trim().charAt(0) || "?"}</span>
      )}
    </span>
  );
}
