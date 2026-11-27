#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "RoomView.h"
#include <d3dcompiler.h>
#include <DirectXMath.h>
#include <wrl/client.h>
#include <atomic>
#include <vector>
#include <fstream>
#include <filesystem>
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <wincodec.h>
#include <Xinput.h>
#include "RoomActor.h"
#pragma comment(lib,"d3d11.lib")
#pragma comment(lib,"d3dcompiler.lib")
#pragma comment(lib,"windowscodecs.lib")
#pragma comment(lib,"ole32.lib")
#pragma comment(lib,"xinput9_1_0.lib")

using Microsoft::WRL::ComPtr;
using namespace DirectX;
namespace RoomView {
#ifdef DIVA_ROOM_TESTING
double previewSeconds=-1;
void PreviewTimeForTest(double seconds){previewSeconds=seconds;}
int MotionForTest(double seconds,float* out){auto s=RoomActor::behaviour(seconds);out[0]=s.b.position.x;out[1]=s.b.position.z;out[2]=s.b.yaw;out[3]=s.look;return s.b.clip;}
int RawMotionForTest(double seconds,float* out){auto s=RoomActor::rawBehaviour(seconds);out[0]=s.b.position.x;out[1]=s.b.position.z;out[2]=s.b.yaw;out[3]=s.look;return s.b.clip;}
#endif
namespace {
HMODULE moduleHandle{};
enum class Phase { Menu, Requested, ExitingMenu, Loading, Finishing, Room, Paused, Leaving };
std::atomic<Phase> phase{Phase::Menu};
LoadingApi loadingApi{};
unsigned (*nativeInput)(){};
bool nativeRenderPass=false;
bool ownsLoading=false;
bool leftMenu=false;
bool ownsMusic=false;
std::atomic<bool> releaseRequested{false},loaded{false},loadFailed{false};
std::atomic<ULONGLONG> resumeAt{0};
// Process-lifetime owners: never call into the graphics driver from CRT
// destruction under the loader lock. Scene contents are cleared during Frame.
// The OS reclaims remaining resources at process exit; hot DLL unload is unsupported.
auto& device=*new ComPtr<ID3D11Device>();
auto& context=*new ComPtr<ID3D11DeviceContext>();
auto& meshVS=*new ComPtr<ID3D11VertexShader>();
auto& overlayVS=*new ComPtr<ID3D11VertexShader>();
auto& meshPS=*new ComPtr<ID3D11PixelShader>();
auto& overlayPS=*new ComPtr<ID3D11PixelShader>();
auto& alphaBlend=*new ComPtr<ID3D11BlendState>();
auto& pauseImages=*new std::array<ComPtr<ID3D11ShaderResourceView>,2>();
auto& layout=*new ComPtr<ID3D11InputLayout>();
auto& constants=*new ComPtr<ID3D11Buffer>();
auto& sampler=*new ComPtr<ID3D11SamplerState>();
auto& raster=*new ComPtr<ID3D11RasterizerState>();
auto& depthOn=*new ComPtr<ID3D11DepthStencilState>();
auto& depthOff=*new ComPtr<ID3D11DepthStencilState>();
auto& depthTexture=*new ComPtr<ID3D11Texture2D>();
auto& depthView=*new ComPtr<ID3D11DepthStencilView>();
UINT width{},height{};
ULONGLONG openedAt{};
std::atomic<ULONGLONG> animationStart{},pausedAt{};
std::atomic<int> pauseSelection{0};
unsigned previousKeys=0;
std::ifstream input;
uint32_t groupCount=0;
XMFLOAT3 eye{},interest{};
float horizontalFov=1.2870022f;
struct Vertex { float position[3],normal[3],uv[2]; };
struct Sample { float offset[3],uv[2],emission; };
struct Group {
    ComPtr<ID3D11Buffer> vertices;
    std::vector<ComPtr<ID3D11ShaderResourceView>> textures;
    std::vector<UINT> durations;
    std::vector<Sample> samples;
    UINT count{},flags{},duration{};
};
auto& groups=*new std::vector<Group>();
auto& actor=*new RoomActor::Actor();
struct alignas(16) Constants { XMFLOAT4X4 matrix; float offset[3],flags,uv[2],emission,padding; };

void check(HRESULT hr) { if(FAILED(hr)) throw std::runtime_error("D3D11 room resource failed"); }
std::filesystem::path folder() {
    wchar_t path[32768]{};
    if(!GetModuleFileNameW(moduleHandle,path,32768)) throw std::runtime_error("Missing module path");
    return std::filesystem::path(path).parent_path()/L"room";
}
void read(std::istream& s,void* p,size_t n) {
    if(!s.read(static_cast<char*>(p),static_cast<std::streamsize>(n))) throw std::runtime_error("Truncated room resource");
}
template<class T> T read(std::istream& s) { T v{};read(s,&v,sizeof(v));return v; }
ComPtr<ID3D11ShaderResourceView> texture(UINT w,UINT h,const unsigned char* pixels) {
    D3D11_TEXTURE2D_DESC desc{};desc.Width=w;desc.Height=h;desc.MipLevels=1;desc.ArraySize=1;
    desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;desc.SampleDesc.Count=1;desc.Usage=D3D11_USAGE_IMMUTABLE;desc.BindFlags=D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA data{pixels,w*4,0};ComPtr<ID3D11Texture2D> tex;
    check(device->CreateTexture2D(&desc,&data,&tex));ComPtr<ID3D11ShaderResourceView> view;
    check(device->CreateShaderResourceView(tex.Get(),nullptr,&view));return view;
}
ComPtr<ID3D11ShaderResourceView> image(const wchar_t* name) {
    struct Apartment {HRESULT result=CoInitializeEx(nullptr,COINIT_MULTITHREADED);~Apartment(){if(SUCCEEDED(result))CoUninitialize();}} apartment;
    ComPtr<IWICImagingFactory> factory;check(CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&factory)));
    ComPtr<IWICBitmapDecoder> decoder;check(factory->CreateDecoderFromFilename((folder()/name).c_str(),nullptr,GENERIC_READ,WICDecodeMetadataCacheOnLoad,&decoder));
    ComPtr<IWICBitmapFrameDecode> frame;check(decoder->GetFrame(0,&frame));UINT w{},h{};check(frame->GetSize(&w,&h));
    if(!w||!h||w>4096||h>4096)throw std::runtime_error("Invalid pause image dimensions");
    ComPtr<IWICFormatConverter> converter;check(factory->CreateFormatConverter(&converter));
    check(converter->Initialize(frame.Get(),GUID_WICPixelFormat32bppRGBA,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeCustom));
    std::vector<unsigned char> pixels(size_t(w)*h*4);check(converter->CopyPixels(nullptr,w*4,UINT(pixels.size()),pixels.data()));
    return texture(w,h,pixels.data());
}
const wchar_t* region() {
    const char* lang="english";auto steam=GetModuleHandleW(L"steam_api64.dll");
    if(steam){auto apps=reinterpret_cast<void*(*)()>(GetProcAddress(steam,"SteamAPI_SteamApps_v008"));auto get=reinterpret_cast<const char*(*)(void*)>(GetProcAddress(steam,"SteamAPI_ISteamApps_GetCurrentGameLanguage"));if(apps&&get)if(auto a=apps())if(auto l=get(a))lang=l;}
    struct Entry{const char* language;const wchar_t* region;};
    for(auto e:{Entry{"spanish",L"sp"},{"latam",L"sp"},{"french",L"fr"},{"german",L"ge"},{"italian",L"it"},{"japanese",L"jp"},{"koreana",L"kr"},{"schinese",L"cn"},{"tchinese",L"tw"}})if(!strcmp(lang,e.language))return e.region;
    return L"en";
}
const char* shader=R"(
cbuffer Params:register(b0) { row_major float4x4 mvp; float3 offset; float flags; float2 uvOffset; float emission; float padding; };
Texture2D tex:register(t0); SamplerState smp:register(s0);
struct V { float3 pos:POSITION; float3 normal:NORMAL; float2 uv:TEXCOORD0; };
struct P { float4 pos:SV_POSITION; float3 normal:NORMAL; float2 uv:TEXCOORD0; float3 world:TEXCOORD1; };
P MeshVS(V v) { P p; p.world=v.pos+offset;p.pos=mul(float4(p.world,1),mvp);p.normal=v.normal;p.uv=v.uv+uvOffset;return p; }
float4 MeshPS(P p):SV_TARGET {
 float4 c=tex.Sample(smp,p.uv);clip(c.a-0.2);
 float3 toLight=float3(0,1.8,0)-p.world;
 float light=.84+.22*saturate(dot(normalize(p.normal),normalize(toLight)))/(1+.08*dot(toLight,toLight));
 float glow=flags==1?saturate((c.g-c.r)*6)*emission*.35:(flags==2?emission*.35:0);
 if(flags==4)light=1;
 return float4(saturate(c.rgb*light+c.rgb*glow),1);
}
P OverlayVS(uint id:SV_VertexID) {
 P p;p.uv=float2((id<<1)&2,id&2);p.pos=float4(p.uv*float2(2,-2)+float2(-1,1),0,1);p.normal=0;p.world=0;return p;
}
float4 OverlayPS(P p):SV_TARGET {float4 c=tex.Sample(smp,p.uv);c.a*=padding;return c;}
)";
ComPtr<ID3DBlob> compile(const char* entry,const char* target) {
    ComPtr<ID3DBlob> blob,errors;
    check(D3DCompile(shader,strlen(shader),"DivaRoom",nullptr,nullptr,entry,target,D3DCOMPILE_ENABLE_STRICTNESS,0,&blob,&errors));return blob;
}
void pipeline() {
    if(meshVS)return;
    auto vs=compile("MeshVS","vs_5_0"),ps=compile("MeshPS","ps_5_0");
    check(device->CreateVertexShader(vs->GetBufferPointer(),vs->GetBufferSize(),nullptr,&meshVS));
    check(device->CreatePixelShader(ps->GetBufferPointer(),ps->GetBufferSize(),nullptr,&meshPS));
    auto ovs=compile("OverlayVS","vs_5_0"),ops=compile("OverlayPS","ps_5_0");
    check(device->CreateVertexShader(ovs->GetBufferPointer(),ovs->GetBufferSize(),nullptr,&overlayVS));
    check(device->CreatePixelShader(ops->GetBufferPointer(),ops->GetBufferSize(),nullptr,&overlayPS));
    D3D11_BLEND_DESC blend{};blend.RenderTarget[0].BlendEnable=TRUE;
    blend.RenderTarget[0].SrcBlend=D3D11_BLEND_SRC_ALPHA;blend.RenderTarget[0].DestBlend=D3D11_BLEND_INV_SRC_ALPHA;blend.RenderTarget[0].BlendOp=D3D11_BLEND_OP_ADD;
    blend.RenderTarget[0].SrcBlendAlpha=D3D11_BLEND_ONE;blend.RenderTarget[0].DestBlendAlpha=D3D11_BLEND_INV_SRC_ALPHA;blend.RenderTarget[0].BlendOpAlpha=D3D11_BLEND_OP_ADD;blend.RenderTarget[0].RenderTargetWriteMask=D3D11_COLOR_WRITE_ENABLE_ALL;
    check(device->CreateBlendState(&blend,&alphaBlend));
    D3D11_INPUT_ELEMENT_DESC elements[]={{"POSITION",0,DXGI_FORMAT_R32G32B32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0},
      {"NORMAL",0,DXGI_FORMAT_R32G32B32_FLOAT,0,12,D3D11_INPUT_PER_VERTEX_DATA,0},
      {"TEXCOORD",0,DXGI_FORMAT_R32G32_FLOAT,0,24,D3D11_INPUT_PER_VERTEX_DATA,0}};
    check(device->CreateInputLayout(elements,3,vs->GetBufferPointer(),vs->GetBufferSize(),&layout));
    D3D11_BUFFER_DESC cb{};cb.ByteWidth=sizeof(Constants);cb.Usage=D3D11_USAGE_DEFAULT;cb.BindFlags=D3D11_BIND_CONSTANT_BUFFER;
    check(device->CreateBuffer(&cb,nullptr,&constants));
    D3D11_SAMPLER_DESC sd{};sd.Filter=D3D11_FILTER_MIN_MAG_MIP_LINEAR;sd.AddressU=sd.AddressV=sd.AddressW=D3D11_TEXTURE_ADDRESS_WRAP;sd.MaxLOD=D3D11_FLOAT32_MAX;
    check(device->CreateSamplerState(&sd,&sampler));
    D3D11_RASTERIZER_DESC rd{};rd.FillMode=D3D11_FILL_SOLID;rd.CullMode=D3D11_CULL_NONE;rd.DepthClipEnable=TRUE;
    check(device->CreateRasterizerState(&rd,&raster));
    D3D11_DEPTH_STENCIL_DESC dd{};dd.DepthEnable=TRUE;dd.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ALL;dd.DepthFunc=D3D11_COMPARISON_LESS_EQUAL;
    check(device->CreateDepthStencilState(&dd,&depthOn));dd.DepthEnable=FALSE;dd.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ZERO;
    check(device->CreateDepthStencilState(&dd,&depthOff));
}
// Preserve every graphics state changed below. No back-buffer reference survives Present.
struct State {
    ID3D11DeviceContext* c;
    ID3D11RenderTargetView* rt[8]{};ID3D11DepthStencilView* ds{};
    ID3D11BlendState* blend{};FLOAT blendFactor[4]{};UINT mask{};
    ID3D11DepthStencilState* depth{};UINT stencil{};
    ID3D11RasterizerState* rs{};UINT nvp=16,nsc=16;D3D11_VIEWPORT vp[16]{};D3D11_RECT sc[16]{};
    ID3D11InputLayout* il{};ID3D11Buffer* vb{};UINT stride{},offset{};D3D11_PRIMITIVE_TOPOLOGY topology{};
    ID3D11VertexShader* vs{};ID3D11PixelShader* ps{};ID3D11GeometryShader* gs{};ID3D11HullShader* hs{};ID3D11DomainShader* dsShader{};
    ID3D11ClassInstance *vci[256]{},*pci[256]{},*gci[256]{},*hci[256]{},*dci[256]{};UINT nv=256,np=256,ng=256,nh=256,nd=256;
    ID3D11Buffer *vcb{},*vcb1{},*pcb{};ID3D11ShaderResourceView* srv{};ID3D11SamplerState* ss{};
    explicit State(ID3D11DeviceContext* value):c(value) {
        c->OMGetRenderTargets(8,rt,&ds);c->OMGetBlendState(&blend,blendFactor,&mask);c->OMGetDepthStencilState(&depth,&stencil);
        c->RSGetState(&rs);c->RSGetViewports(&nvp,vp);c->RSGetScissorRects(&nsc,sc);
        c->IAGetInputLayout(&il);c->IAGetVertexBuffers(0,1,&vb,&stride,&offset);c->IAGetPrimitiveTopology(&topology);
        c->VSGetShader(&vs,vci,&nv);c->PSGetShader(&ps,pci,&np);c->GSGetShader(&gs,gci,&ng);c->HSGetShader(&hs,hci,&nh);c->DSGetShader(&dsShader,dci,&nd);
        c->VSGetConstantBuffers(0,1,&vcb);c->PSGetConstantBuffers(0,1,&pcb);c->PSGetShaderResources(0,1,&srv);c->PSGetSamplers(0,1,&ss);
        c->VSGetConstantBuffers(1,1,&vcb1);
    }
    template<class T> static void release(T* p) { if(p)p->Release(); }
    ~State() {
        c->OMSetRenderTargets(8,rt,ds);c->OMSetBlendState(blend,blendFactor,mask);c->OMSetDepthStencilState(depth,stencil);
        c->RSSetState(rs);c->RSSetViewports(nvp,vp);c->RSSetScissorRects(nsc,sc);
        c->IASetInputLayout(il);c->IASetVertexBuffers(0,1,&vb,&stride,&offset);c->IASetPrimitiveTopology(topology);
        c->VSSetShader(vs,vci,nv);c->PSSetShader(ps,pci,np);c->GSSetShader(gs,gci,ng);c->HSSetShader(hs,hci,nh);c->DSSetShader(dsShader,dci,nd);
        c->VSSetConstantBuffers(0,1,&vcb);c->PSSetConstantBuffers(0,1,&pcb);c->PSSetShaderResources(0,1,&srv);c->PSSetSamplers(0,1,&ss);
        c->VSSetConstantBuffers(1,1,&vcb1);release(vcb1);
        for(auto p:rt)release(p);release(ds);release(blend);release(depth);release(rs);release(il);release(vb);
        release(vs);release(ps);release(gs);release(hs);release(dsShader);release(vcb);release(pcb);release(srv);release(ss);
        for(UINT i=0;i<nv;i++)release(vci[i]);for(UINT i=0;i<np;i++)release(pci[i]);for(UINT i=0;i<ng;i++)release(gci[i]);
        for(UINT i=0;i<nh;i++)release(hci[i]);for(UINT i=0;i<nd;i++)release(dci[i]);
    }
};
void beginLoad() {
    input.open(folder()/L"room.mesh",std::ios::binary);char magic[8]{};read(input,magic,8);
    if(memcmp(magic,"DRROOM2\0",8))throw std::runtime_error("Unknown room format");
    groupCount=read<uint32_t>(input);if(groupCount==0||groupCount>256)throw std::runtime_error("Invalid material count");
    eye=read<XMFLOAT3>(input);interest=read<XMFLOAT3>(input);horizontalFov=read<float>(input);
    if(!std::isfinite(horizontalFov)||horizontalFov<.1f||horizontalFov>3.f)throw std::runtime_error("Invalid camera");
}
void loadGroup() {
    UINT n=read<uint32_t>(input),w=read<uint32_t>(input),h=read<uint32_t>(input),flags=read<uint32_t>(input);
    UINT sampleCount=read<uint32_t>(input),textureCount=read<uint32_t>(input);
    if(!n||n>3000000||n%3||!w||!h||w>4096||h>4096)throw std::runtime_error("Invalid mesh batch");
    std::vector<Vertex> vertices(n);read(input,vertices.data(),vertices.size()*sizeof(Vertex));
    if((sampleCount!=1&&sampleCount!=361)||!textureCount||textureCount>64||flags>4)throw std::runtime_error("Invalid animation");
    Group g{};g.count=n;g.flags=flags;g.samples.resize(sampleCount);
    read(input,g.samples.data(),sizeof(Sample)*sampleCount);
    for(auto& sample:g.samples)for(float v: {sample.offset[0],sample.offset[1],sample.offset[2],sample.uv[0],sample.uv[1],sample.emission})
        if(!std::isfinite(v))throw std::runtime_error("Invalid animation value");
    std::vector<unsigned char> pixels(size_t(w)*h*4);
    for(UINT i=0;i<textureCount;i++) {
        UINT duration=read<UINT>(input);if(!duration||duration>60000)throw std::runtime_error("Invalid texture duration");
        g.durations.push_back(duration);g.duration+=duration;
        read(input,pixels.data(),pixels.size());g.textures.push_back(texture(w,h,pixels.data()));
    }
    D3D11_BUFFER_DESC desc{};desc.ByteWidth=n*sizeof(Vertex);desc.Usage=D3D11_USAGE_IMMUTABLE;desc.BindFlags=D3D11_BIND_VERTEX_BUFFER;
    D3D11_SUBRESOURCE_DATA data{vertices.data(),0,0};check(device->CreateBuffer(&desc,&data,&g.vertices));groups.push_back(std::move(g));
    if(groups.size()==groupCount){
        input.close();
        for(int i=0;i<2;i++){auto name=std::wstring(L"pause-")+region()+L"-"+std::to_wstring(i)+L".png";pauseImages[i]=image(name.c_str());}
        actor.load(device.Get(),folder()/L"miku.actor");
        loaded=true;
    }
}
void clearRoom() { input.close();input.clear();groups.clear();actor.clear();for(auto& p:pauseImages)p.Reset();groupCount=0;loaded=false;loadFailed=false; }
void close() { phase=Phase::Leaving; }
void draw(ID3D11DeviceContext* c,ID3D11RenderTargetView* rtv) {
    ComPtr<ID3D11Resource> resource;rtv->GetResource(&resource);
    ComPtr<ID3D11Texture2D> back;check(resource.As(&back));
    D3D11_TEXTURE2D_DESC bd{};back->GetDesc(&bd);
    if(width!=bd.Width||height!=bd.Height||!depthView) {
        depthView.Reset();depthTexture.Reset();width=bd.Width;height=bd.Height;
        D3D11_TEXTURE2D_DESC dd{};dd.Width=width;dd.Height=height;dd.MipLevels=1;dd.ArraySize=1;dd.Format=DXGI_FORMAT_D24_UNORM_S8_UINT;
        dd.SampleDesc=bd.SampleDesc;dd.Usage=D3D11_USAGE_DEFAULT;dd.BindFlags=D3D11_BIND_DEPTH_STENCIL;
        check(device->CreateTexture2D(&dd,nullptr,&depthTexture));check(device->CreateDepthStencilView(depthTexture.Get(),nullptr,&depthView));
    }
    State saved(c);
    c->OMSetRenderTargets(1,&rtv,depthView.Get());c->OMSetBlendState(nullptr,nullptr,0xffffffff);
    float bg[]={.025f,.05f,.065f,1};c->ClearRenderTargetView(rtv,bg);c->ClearDepthStencilView(depthView.Get(),D3D11_CLEAR_DEPTH,1,0);
    D3D11_VIEWPORT viewport{0,0,float(width),float(height),0,1};c->RSSetViewports(1,&viewport);c->RSSetState(raster.Get());
    c->GSSetShader(nullptr,nullptr,0);c->HSSetShader(nullptr,nullptr,0);c->DSSetShader(nullptr,nullptr,0);
    c->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    auto* cb=constants.Get();c->VSSetConstantBuffers(0,1,&cb);c->PSSetConstantBuffers(0,1,&cb);auto* s=sampler.Get();c->PSSetSamplers(0,1,&s);
    Constants params{};
    {
        ULONGLONG elapsed=(phase==Phase::Paused?pausedAt.load():GetTickCount64())-animationStart.load();
#ifdef DIVA_ROOM_TESTING
        if(previewSeconds>=0)elapsed=ULONGLONG(previewSeconds*1000);
#endif
        float frame=float(elapsed%12000)*.03f;
        float aspect=float(width)/height;float fovy=2*atanf(tanf((actor.ready()?1.55f:horizontalFov)*.5f)/aspect);
        XMFLOAT3 cameraEye=eye,cameraInterest=interest;actor.camera(elapsed*.001,cameraEye,cameraInterest);
        auto view=XMMatrixLookAtRH(XMLoadFloat3(&cameraEye),XMLoadFloat3(&cameraInterest),XMVectorSet(0,1,0,0));
        auto projection=XMMatrixPerspectiveFovRH(fovy,aspect,.01f,100.f);XMStoreFloat4x4(&params.matrix,view*projection);
        c->OMSetDepthStencilState(depthOn.Get(),0);c->IASetInputLayout(layout.Get());c->VSSetShader(meshVS.Get(),nullptr,0);c->PSSetShader(meshPS.Get(),nullptr,0);
        for(auto& g:groups) {
            UINT a=g.samples.size()==1?0:UINT(frame),b=g.samples.size()==1?0:a+1;
            float weight=g.samples.size()==1?0:frame-a;
            for(int i=0;i<3;i++)params.offset[i]=g.samples[a].offset[i]+weight*(g.samples[b].offset[i]-g.samples[a].offset[i]);
            for(int i=0;i<2;i++)params.uv[i]=g.samples[a].uv[i]+weight*(g.samples[b].uv[i]-g.samples[a].uv[i]);
            params.emission=g.samples[a].emission+weight*(g.samples[b].emission-g.samples[a].emission);
            params.flags=float(g.flags);c->UpdateSubresource(cb,0,nullptr,&params,0,0);
            UINT stride=sizeof(Vertex),offset=0;auto* vb=g.vertices.Get();c->IASetVertexBuffers(0,1,&vb,&stride,&offset);
            UINT t=UINT(elapsed%g.duration),index=0;
            while(index+1<g.durations.size()&&t>=g.durations[index]){t-=g.durations[index];++index;}
            auto* view=g.textures[index].Get();c->PSSetShaderResources(0,1,&view);c->Draw(g.count,0);
        }
        actor.draw(c,view*projection,elapsed*.001);
        c->VSSetConstantBuffers(0,1,&cb);c->PSSetConstantBuffers(0,1,&cb);
    }
    if(phase==Phase::Paused) {
        params.padding=std::min(1.f,float(GetTickCount64()-pausedAt.load())/130.f);
        c->UpdateSubresource(cb,0,nullptr,&params,0,0);c->OMSetDepthStencilState(depthOff.Get(),0);c->OMSetBlendState(alphaBlend.Get(),nullptr,0xffffffff);
        c->IASetInputLayout(nullptr);c->VSSetShader(overlayVS.Get(),nullptr,0);c->PSSetShader(overlayPS.Get(),nullptr,0);
        auto* image=pauseImages[pauseSelection.load()].Get();c->PSSetShaderResources(0,1,&image);c->Draw(3,0);
    }
}
unsigned keyboardKeys() {
    DWORD pid{};GetWindowThreadProcessId(GetForegroundWindow(),&pid);if(pid!=GetCurrentProcessId())return 0;
    unsigned result=0;
    if(GetAsyncKeyState(VK_ESCAPE)&0x8000)result|=1;
    if(GetAsyncKeyState(VK_UP)&0x8000)result|=2;
    if(GetAsyncKeyState(VK_DOWN)&0x8000)result|=4;
    if(GetAsyncKeyState(VK_RETURN)&0x8000)result|=8;
    return result;
}
unsigned keys() {
    DWORD pid{};GetWindowThreadProcessId(GetForegroundWindow(),&pid);if(pid!=GetCurrentProcessId())return 0;
    unsigned result=keyboardKeys();
    XINPUT_STATE state{};
    for(DWORD i=0;i<XUSER_MAX_COUNT;i++)if(XInputGetState(i,&state)==ERROR_SUCCESS) {
        auto b=state.Gamepad.wButtons;
        if(b&XINPUT_GAMEPAD_START)result|=1;
        if((b&XINPUT_GAMEPAD_DPAD_UP)||state.Gamepad.sThumbLY>16000)result|=2;
        if((b&XINPUT_GAMEPAD_DPAD_DOWN)||state.Gamepad.sThumbLY< -16000)result|=4;
        if(b&XINPUT_GAMEPAD_A)result|=8;
        if(b&XINPUT_GAMEPAD_B)result|=16;
    }
    return result;
}
void sound(int kind){if(loadingApi.sound)loadingApi.sound(kind);}
}
void SetModule(HMODULE module) { moduleHandle=module; }
void Initialize(IDXGISwapChain*,ID3D11Device* d,ID3D11DeviceContext* c) { device=d;context=c; }
void SetLoadingApi(LoadingApi api) { loadingApi=api; }
void SetInputReader(unsigned (*pressed)()){nativeInput=pressed;previousKeys=0;}
bool BlocksMenu() { return phase!=Phase::Menu||GetTickCount64()<resumeAt.load(); }
void Open() { auto expected=Phase::Menu;phase.compare_exchange_strong(expected,Phase::Requested); }
bool IsPaused(){return phase==Phase::Paused;}
bool ReleaseScene(){
    if(ownsMusic){loadingApi.stopMusic();ownsMusic=false;}
    if(ownsLoading){loadingApi.reset();ownsLoading=false;}
    leftMenu=false;
    if(phase.exchange(Phase::Menu)!=Phase::Menu)releaseRequested=true;
    // Scene teardown must not wait for Present: shutdown can stop rendering
    // before invoking dest. Visuals are already disabled by Phase::Menu;
    // release GPU resources on the next render callback, if there is one.
    return true;
}
void Act(Action action) {
    if(phase==Phase::Room&&(action==Action::Pause||action==Action::Cancel)){
        pausedAt=GetTickCount64();pauseSelection=0;phase=Phase::Paused;sound(3);return;
    }
    if(phase!=Phase::Paused)return;
    if(action==Action::Up||action==Action::Down){pauseSelection=1-pauseSelection.load();sound(2);return;}
    if(action==Action::Pause||action==Action::Cancel||(action==Action::Accept&&pauseSelection==0)){
        animationStart.fetch_add(GetTickCount64()-pausedAt.load());phase=Phase::Room;sound(action==Action::Accept?0:1);return;
    }
    if(action==Action::Accept){sound(0);close();}
}
void Update() {
    unsigned held=0,pressed=0;
    if(nativeInput){
        DWORD pid{};GetWindowThreadProcessId(GetForegroundWindow(),&pid);
        if(pid==GetCurrentProcessId())pressed=nativeInput();
        // Steam Input can leave native keyboard actions inactive while a pad
        // is selected. Keep keyboard press edges alongside native pad events.
        held=keyboardKeys();pressed|=held&~previousKeys;previousKeys=held;
    }else{held=keys();pressed=held&~previousKeys;previousKeys=held;}
    if(pressed&1)Act(Action::Pause);
    else if(pressed&16)Act(Action::Cancel);
    else if(pressed&2)Act(Action::Up);
    else if(pressed&4)Act(Action::Down);
    else if(pressed&8)Act(Action::Accept);
    switch(phase.load()) {
    case Phase::Requested:
        if(releaseRequested)return;
        if(loadingApi.leaveMenu)loadingApi.leaveMenu();leftMenu=true;
        openedAt=GetTickCount64();phase=Phase::ExitingMenu;break;
    case Phase::ExitingMenu:
        if(loadingApi.menuExited&&!loadingApi.menuExited()&&GetTickCount64()-openedAt<2500)break;
        if(loadingApi.begin&&!loadingApi.begin()){phase=Phase::Leaving;break;}
        ownsLoading=loadingApi.begin!=nullptr;openedAt=GetTickCount64();phase=Phase::Loading;break;
    case Phase::Loading:
        if(loadFailed){phase=Phase::Leaving;break;}
        if(loaded&&GetTickCount64()-openedAt>=700){if(ownsLoading)loadingApi.finish();phase=Phase::Finishing;}
        break;
    case Phase::Finishing:
        if(!ownsLoading||loadingApi.finished()) {
            if(ownsLoading)loadingApi.reset();ownsLoading=false;
            animationStart=GetTickCount64();phase=Phase::Room;
            ownsMusic=loadingApi.startMusic&&loadingApi.stopMusic&&loadingApi.startMusic();
        }
        break;
    case Phase::Leaving:
        if(ownsLoading){loadingApi.reset();ownsLoading=false;}
        if(ownsMusic){loadingApi.stopMusic();ownsMusic=false;}
        if(leftMenu&&loadingApi.returnMenu)loadingApi.returnMenu();leftMenu=false;
        releaseRequested=true;resumeAt=GetTickCount64()+300;phase=Phase::Menu;break;
    default:break;
    }
    if(ownsMusic&&loadingApi.updateMusic)loadingApi.updateMusic();
}
void Resized() { depthView.Reset();depthTexture.Reset();width=height=0; }
void UseNativeRenderPass(){nativeRenderPass=true;}
bool HasRoomVisuals(){return loaded&&(phase==Phase::Room||phase==Phase::Paused);}
void RenderNative(ID3D11DeviceContext* c){
    if(!HasRoomVisuals()||!c)return;
    try {
        ComPtr<ID3D11RenderTargetView> target;c->OMGetRenderTargets(1,&target,nullptr);
        if(target)draw(c,target.Get());
    }catch(...){loadFailed=true;close();}
}
void Frame(IDXGISwapChain* swap) {
    if(releaseRequested.exchange(false))clearRoom();
    const auto current=phase.load();
    if(current==Phase::Menu||current==Phase::Requested||current==Phase::ExitingMenu||current==Phase::Leaving)return;
    try {
        if(!device){check(swap->GetDevice(IID_PPV_ARGS(&device)));device->GetImmediateContext(&context);}
        pipeline();
        // WAIT_SCREEN owns loading visuals. Never cover its native AETs.
        if(current==Phase::Loading&&!loadFailed) {
            try { if(!groupCount)beginLoad();if(!loaded)loadGroup(); }
            catch(...) {loadFailed=true;input.close();}
        }
        if(!nativeRenderPass&&(current==Phase::Room||current==Phase::Paused)){
            ComPtr<ID3D11Texture2D> back;check(swap->GetBuffer(0,IID_PPV_ARGS(&back)));
            ComPtr<ID3D11RenderTargetView> target;check(device->CreateRenderTargetView(back.Get(),nullptr,&target));
            draw(context.Get(),target.Get());
        }
    } catch(...) {
        close();MessageBoxW(nullptr,L"No se pudo preparar la vista 3D de DIVA ROOM.",L"DIVA ROOM",MB_OK|MB_ICONERROR);
    }
}
}
