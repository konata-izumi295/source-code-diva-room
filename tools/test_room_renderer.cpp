#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d11.h>
#include <wrl/client.h>
#include <fstream>
#include <string>
#include <cassert>
#include <cmath>
#include <set>
#include "../DivaRoom/RoomView.h"
#pragma comment(lib,"d3d11.lib")
using Microsoft::WRL::ComPtr;
namespace RoomView {void PreviewTimeForTest(double seconds);int MotionForTest(double seconds,float* out);int RawMotionForTest(double seconds,float* out);}
int begins=0,finishes=0,resets=0,leaves=0,returns=0;
int musicStarts=0,musicStops=0,musicUpdates=0;
bool playing=false,audioOrderError=false;
bool startMusic(){if(playing)audioOrderError=true;playing=true;++musicStarts;return true;}
void updateMusic(){if(!playing)audioOrderError=true;++musicUpdates;}
void stopMusic(){if(!playing)audioOrderError=true;playing=false;++musicStops;}
bool begin(){++begins;return true;}void finish(){++finishes;}bool finished(){return true;}void reset(){++resets;}
void leave(){++leaves;}void back(){if(playing)audioOrderError=true;++returns;}void sound(int){}bool exited(){return true;}
int main() {
    int motionFailure=0;
    float maxWalkingSpeed=0,maxWalkingYaw=0,maxLookRate=0,maxWalkingYawAcceleration=0,previousSignedYaw=0;
    float maxRawYawAcceleration=0,previousRawYaw=0,previousRawSignedYaw=0,maxHeadingAdjustment=0;
    // Sample two minutes at 120 Hz: locomotion must not teleport or exceed
    // the intended walking speed, including segment boundaries.
    std::ofstream motion("motion-validation.csv");motion<<"time,clip,speed,yaw_rate,look,x,z,yaw\n";
    float previous[4]{};int previousClip=RoomView::MotionForTest(0,previous),previousPreviousClip=previousClip;
    previousRawYaw=previous[2];
    for(int i=1;i<=14400;i++){
        float p[4]{};int clip=RoomView::MotionForTest(i/120.0,p);
        float raw[4]{};int rawClip=RoomView::RawMotionForTest(i/120.0,raw);
        // Body smoothing must never change the route or action selection.
        if(rawClip!=clip||raw[0]!=p[0]||raw[1]!=p[1])return 22;
        maxHeadingAdjustment=std::max(maxHeadingAdjustment,std::abs(std::remainder(p[2]-raw[2],6.283185307f)));
        float rawSignedYaw=std::remainder(raw[2]-previousRawYaw,6.283185307f)*120;
        float speed=std::hypot(p[0]-previous[0],p[1]-previous[1])*120;
        float signedYaw=std::remainder(p[2]-previous[2],6.283185307f)*120;
        float yaw=std::abs(signedYaw);
        float lookRate=std::abs(p[3]-previous[3])*120;
        maxLookRate=std::max(maxLookRate,lookRate);
        if(!std::isfinite(speed)||!std::isfinite(yaw))return 19;
        if(!std::isfinite(lookRate)||lookRate>3.f){
            motionFailure=21;
            if(!GetEnvironmentVariableW(L"DIVA_MOTION_REVIEW",nullptr,0))return 21;
        }
        if((clip==1||clip==9)&&(previousClip==1||previousClip==9)){
            maxWalkingSpeed=std::max(maxWalkingSpeed,speed);
            maxWalkingYaw=std::max(maxWalkingYaw,yaw);
            if(speed>.35f||yaw>3.5f){
                motionFailure=20;
                if(!GetEnvironmentVariableW(L"DIVA_MOTION_REVIEW",nullptr,0))return 20;
            }
        }
        if(clip==1&&previousClip==1&&previousPreviousClip==1){
            maxWalkingYawAcceleration=std::max(maxWalkingYawAcceleration,std::abs(signedYaw-previousSignedYaw)*120);
            maxRawYawAcceleration=std::max(maxRawYawAcceleration,std::abs(rawSignedYaw-previousRawSignedYaw)*120);
        }
        if(i%4==0)motion<<i/120.0<<','<<clip<<','<<speed<<','<<yaw<<','<<p[3]<<','<<p[0]<<','<<p[1]<<','<<p[2]<<'\n';
        for(int j=0;j<4;j++)previous[j]=p[j];previousPreviousClip=previousClip;previousClip=clip;previousSignedYaw=signedYaw;
        previousRawYaw=raw[2];previousRawSignedYaw=rawSignedYaw;
    }
    std::ofstream("motion-summary.json")<<"{\"max_walking_speed\":"<<maxWalkingSpeed
        <<",\"max_walking_yaw_radians_per_second\":"<<maxWalkingYaw
        <<",\"max_look_radians_per_second\":"<<maxLookRate
        <<",\"max_walking_yaw_acceleration\":"<<maxWalkingYawAcceleration
        <<",\"baseline_yaw_acceleration\":"<<maxRawYawAcceleration
        <<",\"max_heading_adjustment\":"<<maxHeadingAdjustment
        <<",\"failure\":"<<motionFailure<<"}\n";
    if(maxWalkingYawAcceleration>35.f||maxHeadingAdjustment>.08f)return 23;
    if(GetEnvironmentVariableW(L"DIVA_MOTION_ONLY",nullptr,0))return motionFailure;
    WNDCLASSW wc{};wc.lpfnWndProc=DefWindowProcW;wc.hInstance=GetModuleHandleW(nullptr);wc.lpszClassName=L"DivaRoomRenderTest";RegisterClassW(&wc);
    HWND window=CreateWindowW(wc.lpszClassName,L"Room validation",WS_OVERLAPPEDWINDOW,0,0,960,540,nullptr,nullptr,wc.hInstance,nullptr);
    DXGI_SWAP_CHAIN_DESC sd{};sd.BufferDesc.Width=960;sd.BufferDesc.Height=540;sd.BufferDesc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;
    sd.SampleDesc.Count=1;sd.BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT;sd.BufferCount=1;sd.OutputWindow=window;sd.Windowed=TRUE;sd.SwapEffect=DXGI_SWAP_EFFECT_DISCARD;
    ComPtr<ID3D11Device> device;ComPtr<ID3D11DeviceContext> ctx;ComPtr<IDXGISwapChain> swap;D3D_FEATURE_LEVEL level;
    HRESULT hr=D3D11CreateDeviceAndSwapChain(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&sd,&swap,&device,&level,&ctx);
    if(FAILED(hr))return 1;
    D3D11_RASTERIZER_DESC rd{};rd.FillMode=D3D11_FILL_WIREFRAME;rd.CullMode=D3D11_CULL_FRONT;rd.DepthClipEnable=TRUE;
    ComPtr<ID3D11RasterizerState> original;device->CreateRasterizerState(&rd,&original);ctx->RSSetState(original.Get());
    D3D11_BUFFER_DESC sentinelDesc{};sentinelDesc.ByteWidth=16;sentinelDesc.Usage=D3D11_USAGE_DEFAULT;sentinelDesc.BindFlags=D3D11_BIND_CONSTANT_BUFFER;
    ComPtr<ID3D11Buffer> sentinel;device->CreateBuffer(&sentinelDesc,nullptr,&sentinel);auto* sentinelPtr=sentinel.Get();ctx->VSSetConstantBuffers(1,1,&sentinelPtr);
    RoomView::SetModule(GetModuleHandleW(nullptr));RoomView::SetLoadingApi({begin,finish,finished,reset,leave,back,sound,exited,startMusic,updateMusic,stopMusic});RoomView::Initialize(swap.Get(),device.Get(),ctx.Get());RoomView::Open();
    for(int i=0;i<100;i++){RoomView::Update();RoomView::Frame(swap.Get());Sleep(16);}
    ComPtr<ID3D11RasterizerState> after;ctx->RSGetState(&after);if(after.Get()!=original.Get())return 2;
    ComPtr<ID3D11Buffer> preservedPalette;ctx->VSGetConstantBuffers(1,1,&preservedPalette);if(preservedPalette.Get()!=sentinel.Get())return 16;
    if(!RoomView::BlocksMenu())return 3;
    RoomView::Resized();RoomView::Frame(swap.Get());
    ComPtr<ID3D11Texture2D> back,staging;swap->GetBuffer(0,IID_PPV_ARGS(&back));D3D11_TEXTURE2D_DESC desc{};back->GetDesc(&desc);
    desc.Usage=D3D11_USAGE_STAGING;desc.BindFlags=0;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;desc.MiscFlags=0;
    if(FAILED(device->CreateTexture2D(&desc,nullptr,&staging)))return 4;
    auto capture=[&](const char* path) {
        ctx->CopyResource(staging.Get(),back.Get());D3D11_MAPPED_SUBRESOURCE map{};
        if(FAILED(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&map)))return uint64_t(0);
        std::ofstream f(path,std::ios::binary);f<<"P6\n"<<desc.Width<<" "<<desc.Height<<"\n255\n";
        uint64_t hash=1469598103934665603ull;
        for(UINT y=0;y<desc.Height;y++)for(UINT x=0;x<desc.Width;x++){
            auto* p=static_cast<unsigned char*>(map.pData)+y*map.RowPitch+x*4;f.write(reinterpret_cast<char*>(p),3);
            for(int i=0;i<3;i++){hash^=p[i];hash*=1099511628211ull;}
        }
        ctx->Unmap(staging.Get(),0);return hash;
    };
    auto first=capture("runtime-room.ppm");Sleep(700);RoomView::Frame(swap.Get());
    if(first==capture("runtime-room-moving.ppm"))return 6;
    RoomView::Act(RoomView::Action::Pause);if(!RoomView::IsPaused())return 7;
    Sleep(150);RoomView::Frame(swap.Get());auto frozen=capture("runtime-paused.ppm");
    Sleep(200);RoomView::Frame(swap.Get());if(frozen!=capture("runtime-paused-again.ppm"))return 8;
    RoomView::Act(RoomView::Action::Accept);if(RoomView::IsPaused())return 9;
    if(musicStarts!=1||musicStops||!playing||musicUpdates==0||audioOrderError)return 30;
    RoomView::Act(RoomView::Action::Pause);RoomView::Act(RoomView::Action::Down);RoomView::Act(RoomView::Action::Accept);
    RoomView::Update();RoomView::Frame(swap.Get());Sleep(350);RoomView::Update();
    if(RoomView::BlocksMenu()||returns!=1||begins!=1||finishes!=1||resets!=1||leaves!=1)return 10;
    if(musicStarts!=1||musicStops!=1||playing||audioOrderError)return 31;
    RoomView::Open();for(int i=0;i<100;i++){RoomView::Update();RoomView::Frame(swap.Get());Sleep(16);}
    if(!RoomView::BlocksMenu()||begins!=2||finishes!=2||resets!=2||leaves!=2)return 11;
    if(musicStarts!=2||musicStops!=1||!playing||audioOrderError)return 32;
    RoomView::Act(RoomView::Action::Pause);RoomView::Act(RoomView::Action::Cancel);if(RoomView::IsPaused())return 12;
    // Native command execution renders to the bound scene target. Present must
    // leave a later native dialog untouched, even when the room is active.
    RoomView::UseNativeRenderPass();
    ComPtr<ID3D11RenderTargetView> rtv;device->CreateRenderTargetView(back.Get(),nullptr,&rtv);
    auto* target=rtv.Get();ctx->OMSetRenderTargets(1,&target,nullptr);
    RoomView::RenderNative(ctx.Get());auto room=capture("runtime-native-room.ppm");
    float dialog[]={.9f,.2f,.3f,1};ctx->ClearRenderTargetView(target,dialog);
    auto overlay=capture("runtime-native-dialog.ppm");if(room==overlay)return 13;
    RoomView::Frame(swap.Get());if(overlay!=capture("runtime-native-dialog-after-present.ppm"))return 14;
    ComPtr<ID3D11RenderTargetView> preserved;ctx->OMGetRenderTargets(1,&preserved,nullptr);
    if(preserved.Get()!=target)return 15;
    for(int second:{0,6,10,11,12,16,26,27,28,29,36,41,46,55,68,75,76,77,78,79,80,82,90,92,93,94,95,98}){
        RoomView::PreviewTimeForTest(second);RoomView::RenderNative(ctx.Get());
        auto name=std::string("actor-")+std::to_string(second)+".ppm";capture(name.c_str());
    }
    for(int frame=0;frame<16;frame++){
        RoomView::PreviewTimeForTest(44+frame/8.0);RoomView::RenderNative(ctx.Get());
        auto name=std::string("reach-")+std::to_string(frame)+".ppm";capture(name.c_str());
    }
    // Discover activities from the current timeline instead of obsolete hard-coded seconds.
    if(GetEnvironmentVariableW(L"DIVA_MOTION_REVIEW",nullptr,0)){
        std::ofstream review("review-frames.csv");review<<"clip,time,path\n";
        std::set<int> reviewed;
        int walkingRuns=0,lastReviewClip=-1;
        for(double t=0;t<120;t+=.05){
            float p[4]{};int clip=RoomView::MotionForTest(t,p);
            if(clip==1&&lastReviewClip!=1)++walkingRuns;
            lastReviewClip=clip;
            // Separate review group for the continuous bed-to-table walk.
            int group=clip==1&&walkingRuns==2?101:clip;
            if(reviewed.count(group)||clip==0||clip==2||clip==3||clip==7)continue;
            double end=t+.05;
            while(end<120&&RoomView::MotionForTest(end,p)==clip)end+=.05;
            if(end-t<.3)continue;
            reviewed.insert(group);
            for(int frame=0;t+frame/8.0<end;frame++){
                RoomView::PreviewTimeForTest(t+frame/8.0);RoomView::RenderNative(ctx.Get());
                auto name=std::string("review-clip")+std::to_string(group)+"-frame"+std::to_string(frame)+".ppm";capture(name.c_str());
                review<<group<<','<<t+frame/8.0<<','<<name<<'\n';
            }
        }
    }
    // Teardown must complete even if no subsequent Present is delivered.
    if(!RoomView::ReleaseScene()||RoomView::HasRoomVisuals())return 17;
    if(!RoomView::ReleaseScene())return 18;
    if(musicStops!=2||playing||audioOrderError)return 33;
    RoomView::Frame(swap.Get());
    DestroyWindow(window);return motionFailure;
}

