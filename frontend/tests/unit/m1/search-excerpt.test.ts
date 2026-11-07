import { describe, expect, it } from 'vitest';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { SearchExcerpt } from '../../../src/components/SearchExcerpt';

describe('Unicode search excerpts rendered as safe text',()=>{
  it('uses code point offsets and escapes HTML without losing the hit',()=>{
    const result=renderToStaticMarkup(createElement(SearchExcerpt,{excerpt:{text:'😀𠀀TCP<script>x</script>',start_offset:5,truncated_after:true,highlights:[{start:2,end:5}]}}));
    expect(result).toBe('…😀𠀀<mark>TCP</mark>&lt;script&gt;x&lt;/script&gt;…');
  });
  it('handles an empty excerpt',()=>{
    expect(renderToStaticMarkup(createElement(SearchExcerpt,{excerpt:{text:'',start_offset:0,truncated_after:false,highlights:[]}}))).toBe('');
  });
});
