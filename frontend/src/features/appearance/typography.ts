/** Installed system fonts only. Missing CJK faces fall back without fetching assets. */
export const fontFamilies={
  ui:'"Times New Roman", Times, "Heiti SC", SimHei, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif',
  reading:'"Times New Roman", Times, "Songti SC", STSong, SimSun, "Noto Serif CJK SC", serif',
  reflection:'"Times New Roman", Times, "Kaiti SC", STKaiti, KaiTi, "Songti SC", STSong, SimSun, serif',
} as const;

/** Installed system-font combinations; no web fonts or external requests. */
export const fontPresets={
  heiti:{
    name:"黑体",
    description:"中文清晰利落，适合界面操作与快速浏览",
    families:{
      ui:'"Times New Roman", Times, "Heiti SC", SimHei, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif',
      reading:'"Times New Roman", Times, "Heiti SC", SimHei, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif',
      reflection:'"Times New Roman", Times, "Heiti SC", SimHei, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif',
    },
  },
  songti:{
    name:"宋体",
    description:"中文端正耐读，适合资料阅读与长文整理",
    families:{
      ui:'"Times New Roman", Times, "Songti SC", STSong, SimSun, "Noto Serif CJK SC", serif',
      reading:'"Times New Roman", Times, "Songti SC", STSong, SimSun, "Noto Serif CJK SC", serif',
      reflection:'"Times New Roman", Times, "Songti SC", STSong, SimSun, "Noto Serif CJK SC", serif',
    },
  },
  kaiti:{
    name:"楷体",
    description:"中文舒展有手稿感，适合思考与复习提示",
    families:{
      ui:'"Times New Roman", Times, "Kaiti SC", STKaiti, KaiTi, "Songti SC", STSong, SimSun, serif',
      reading:'"Times New Roman", Times, "Kaiti SC", STKaiti, KaiTi, "Songti SC", STSong, SimSun, serif',
      reflection:'"Times New Roman", Times, "Kaiti SC", STKaiti, KaiTi, "Songti SC", STSong, SimSun, serif',
    },
  },
} as const;

export type FontPreset=keyof typeof fontPresets;
export type FontScale="small"|"medium"|"large";
