/** Installed system fonts only. Missing CJK faces fall back without fetching assets. */
export const fontFamilies={
  ui:'"Times New Roman", Times, "Heiti SC", SimHei, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif',
  reading:'"Times New Roman", Times, "Songti SC", STSong, SimSun, "Noto Serif CJK SC", serif',
  reflection:'"Times New Roman", Times, "Kaiti SC", STKaiti, KaiTi, "Songti SC", STSong, SimSun, serif',
} as const;
