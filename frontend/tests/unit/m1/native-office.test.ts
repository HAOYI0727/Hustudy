import {describe,it,expect} from 'vitest';
import {officeFrameDocument} from '../../../src/features/materials/office/frame';
describe('Office frame boundaries',()=>{
  it('executes only trusted nonce script and blocks remote resources',()=>{
    const html=officeFrameDocument('const value="</script><img src=x>";','channel-123','nonce-456');
    expect(html).toContain("script-src 'nonce-nonce-456'");
    expect(html).toContain("connect-src 'none'");expect(html).toContain("frame-src 'none'");
    expect(html).toContain('img-src data: blob:');
    expect(html).not.toContain('allow-same-origin');
    expect(html).toContain('<\\/script><img src=x>');
    expect(html.match(/<\/script>/g)).toHaveLength(1);
  });
  it('rejects injectable identifiers',()=>{
    expect(()=>officeFrameDocument('','"><img>','nonce')).toThrow();
    expect(()=>officeFrameDocument('','channel',"nonce' unsafe-inline")).toThrow();
  });
});
