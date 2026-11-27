#pragma once
#include <array>
#include <string>
#include "RoomActorBones.h"

// Room-only rendering and behaviour. No addresses or native game state changes.
namespace RoomActor {
using namespace DirectX;
using Microsoft::WRL::ComPtr;
struct Vertex {float p[3],n[3],uv[2];uint32_t bone[4];float weight[4];};
static_assert(sizeof(Vertex)==64);
struct Batch {ComPtr<ID3D11Buffer> vertices;ComPtr<ID3D11ShaderResourceView> texture;UINT count;};
struct Clip {std::string name;UINT frames;float duration;std::vector<XMFLOAT4X4> matrices;};
struct Pose {int clip=0;XMFLOAT3 position{.65f,.025f,.7f};float yaw=0,recline=0,phone=0;float bedPhase=-1;};
inline float smooth(float x){x=std::clamp(x,0.f,1.f);return x*x*(3-2*x);}
// A soft angular limit avoids a sharp change of neck speed at full anticipation.
inline float gazeOffset(float angle){return .35f*tanhf(angle/.35f);}
inline XMMATRIX orientation(const Pose& p){
    if(p.bedPhase<0)return XMMatrixRotationX(-XM_PIDIV2*p.recline)*XMMatrixRotationY(p.yaw);
    // Roll onto the side before pushing up. Reverse this path for lying down.
    auto lying=XMQuaternionRotationMatrix(XMMatrixRotationX(-XM_PIDIV2)*XMMatrixRotationY(XM_PIDIV2));
    auto side=XMQuaternionRotationMatrix(XMMatrixRotationZ(-XM_PIDIV2)*XMMatrixRotationY(XM_PI));
    auto seated=XMQuaternionRotationMatrix(XMMatrixRotationY(XM_PI));
    auto q=XMQuaternionSlerp(lying,side,smooth(p.bedPhase/1.f));
    q=XMQuaternionSlerp(q,seated,smooth((p.bedPhase-1.f)/1.4f));
    return XMMatrixRotationQuaternion(q);
}
inline Pose mix(Pose a,Pose b,float t){
    a.position={a.position.x+(b.position.x-a.position.x)*t,a.position.y+(b.position.y-a.position.y)*t,a.position.z+(b.position.z-a.position.z)*t};
    a.yaw+=std::remainder(b.yaw-a.yaw,XM_2PI)*t;a.recline+=(b.recline-a.recline)*t;a.phone+=(b.phone-a.phone)*t;return a;
}
struct Sample {Pose a,b;float weight=0;float local=0;bool tablePhone=false;float gait=0;float look=0;float fromTime=-1;float walkTime=0,walkRemaining=0;};
inline XMFLOAT4X4 blendRigid(const XMFLOAT4X4& a,const XMFLOAT4X4& b,float t){
    XMVECTOR sa,qa,pa,sb,qb,pb;XMFLOAT4X4 out;
    if(XMMatrixDecompose(&sa,&qa,&pa,XMLoadFloat4x4(&a))&&XMMatrixDecompose(&sb,&qb,&pb,XMLoadFloat4x4(&b)))
        XMStoreFloat4x4(&out,XMMatrixAffineTransformation(XMVectorLerp(sa,sb,t),XMVectorZero(),XMQuaternionSlerp(qa,qb,t),XMVectorLerp(pa,pb,t)));
    else {const float* x=&a._11;const float* y=&b._11;float* z=&out._11;for(int i=0;i<16;i++)z[i]=x[i]+(y[i]-x[i])*t;}
    return out;
}
// Coordinates use the exported room's Y-up space. Routes pass the right side
// of the central table and approach the foot of the bed from its clear side.
inline Sample rawBehaviour(double seconds){
    struct Step {float duration;Pose target;bool tablePhone;};
    static const Step steps[]={
        {5,{0,{.65f,.025f,.7f},0,0,0},false},
        // Reach the clear aisle first. The bed frame starts at z=.710763;
        // a direct arc from the right side cut through its front corner.
        {2,{1,{.32f,.025f,.46f},-XM_PIDIV2,0,0},false},
        {4,{1,{-.37f,.025f,.52f},XM_PI,0,0},false},
        {6,{8,{.02f,.28f,1.05f},XM_PIDIV2,1,1},false},
        {14,{3,{.02f,.28f,1.05f},XM_PIDIV2,1,1},false},
        {5,{10,{-.37f,.025f,.52f},XM_PI,0,0},false},
        {2,{1,{.32f,.025f,.46f},XM_PIDIV2,0,0},false},
        {3,{1,{.70f,.025f,.58f},XM_PI,0,0},false},
        {4,{1,{.628f,.025f,-.32f},-XM_PIDIV2,0,0},false},
        {7,{2,{.628f,.025f,-.32f},-XM_PIDIV2,0,1},false},
        {4,{5,{.628f,.025f,-.32f},-XM_PIDIV2,0,1},false},
        {3,{1,{.70f,.025f,.45f},0,0,0},true},
        {14,{4,{.70f,.025f,.45f},0,0,0},true},
        {4,{1,{.628f,.025f,-.32f},-XM_PIDIV2,0,0},true},
        {4,{6,{.628f,.025f,-.32f},-XM_PIDIV2,0,1},false},
        {3,{1,{.14f,.025f,.09f},XM_PI,0,1},false},
        {3,{11,{.14f,.025f,.09f},XM_PI,0,0},false},
        {2,{13,{.14f,.025f,.09f},XM_PI,0,1},false},
        {12,{7,{.14f,.025f,.09f},XM_PI,0,1},false},
        {3,{12,{.14f,.025f,.09f},XM_PI,0,0},false},
        {3,{1,{.50f,.025f,.25f},0,0,0},false},
        {4,{1,{.65f,.025f,.7f},0,0,0},false},
    };
    // Arc-length sampled curves keep cadence tied to distance, including turns.
    struct Route {
        float distance=0,heading=0,travel=0,rampIn=.28f,rampOut=.32f;
        XMFLOAT3 p0{},p1{},p2{},p3{};
        std::array<float,129> arc{};
        XMFLOAT3 point(float u)const{
            float v=1-u;return {v*v*v*p0.x+3*v*v*u*p1.x+3*v*u*u*p2.x+u*u*u*p3.x,p0.y,
                v*v*v*p0.z+3*v*v*u*p1.z+3*v*u*u*p2.z+u*u*u*p3.z};
        }
        float tangent(float u)const{
            float v=1-u;
            return atan2f(v*v*(p1.x-p0.x)+2*v*u*(p2.x-p1.x)+u*u*(p3.x-p2.x),
                v*v*(p1.z-p0.z)+2*v*u*(p2.z-p1.z)+u*u*(p3.z-p2.z));
        }
        float parameter(float d)const{
            for(size_t j=1;j<arc.size();j++)if(d<=arc[j])
                return (float(j-1)+(d-arc[j-1])/std::max(1e-6f,arc[j]-arc[j-1]))/128.f;
            return 1;
        }
    };
    static const auto routes=[](){
        std::array<Route,std::size(steps)> result{};
        for(size_t i=0;i<std::size(steps);i++){
            if(steps[i].target.clip!=1)continue;
            auto& r=result[i];auto prior=steps[(i+std::size(steps)-1)%std::size(steps)].target;
            r.p0=prior.position;r.p3=steps[i].target.position;
            float dx=r.p3.x-r.p0.x,dz=r.p3.z-r.p0.z,chord=hypotf(dx,dz);
            r.heading=atan2f(dx,dz);float start=r.heading,end=r.heading;
            if(prior.clip==1){
                auto before=steps[(i+std::size(steps)-2)%std::size(steps)].target.position;
                float incoming=atan2f(r.p0.x-before.x,r.p0.z-before.z);
                start=incoming+.5f*std::remainder(r.heading-incoming,XM_2PI);r.rampIn=0;
            }
            if(i+1<std::size(steps)&&steps[i+1].target.clip==1){
                auto next=steps[i+1].target.position;
                float outgoing=atan2f(next.x-r.p3.x,next.z-r.p3.z);
                end=r.heading+.5f*std::remainder(outgoing-r.heading,XM_2PI);r.rampOut=0;
            }else if((i+1==std::size(steps)||steps[i+1].target.clip!=8)&&
                fabsf(std::remainder(steps[i].target.yaw-r.heading,XM_2PI))<1.8f)
                end=steps[i].target.yaw;
            // Spread changes of heading over several steps instead of
            // concentrating the curve in the last few centimetres.
            float handle=std::min(.28f,chord*.38f);
            r.p1={r.p0.x+sinf(start)*handle,r.p0.y,r.p0.z+cosf(start)*handle};
            r.p2={r.p3.x-sinf(end)*handle,r.p3.y,r.p3.z-cosf(end)*handle};
            auto last=r.p0;
            for(size_t j=1;j<r.arc.size();j++){
                auto pt=r.point(float(j)/128);r.arc[j]=r.arc[j-1]+hypotf(pt.x-last.x,pt.z-last.z);last=pt;
            }
            r.distance=r.arc.back();r.travel=r.distance/.32f+.5f*(r.rampIn+r.rampOut);
        }
        return result;
    }();
    std::array<float,std::size(steps)> durations{};float length=0;
    for(size_t i=0;i<std::size(steps);i++){
        durations[i]=steps[i].target.clip==1?routes[i].travel:steps[i].duration;length+=durations[i];
    }
    float t=float(std::fmod(std::max(0.,seconds),length));Pose previous=steps[std::size(steps)-1].target;float lastGait=0;
    for(size_t index=0;index<std::size(steps);index++){
        Step step=steps[index];step.duration=durations[index];auto& route=routes[index];
        if(t<step.duration){
            float move=smooth(t/step.duration);Pose current=mix(previous,step.target,move);current.clip=step.target.clip;
            Pose old=current;old.clip=previous.clip;
            float weight=smooth(t/.45f),gait=lastGait,look=0,fromTime=-1;
            if(step.target.clip==8||step.target.clip==10){
                // Supported side entry/exit, authored in the same pelvis frame.
                float phase=step.target.clip==8?(t<1.2f?5.f-1.6f*t/1.2f:t<1.65f?3.4f:t<1.9f?3.4f-(t-1.65f)/.25f:t<3.25f?2.4f-1.4f*(t-1.9f)/1.35f:std::max(0.f,1.f-(t-3.25f)/1.10f)):t;
                float sit=smooth((phase-1.f)/1.4f),swing=smooth((phase-1.f)/1.4f),stand=smooth((phase-3.4f)/1.6f);
                current=step.target;current.recline=1-sit;current.yaw=XM_PIDIV2+XM_PIDIV2*swing;current.bedPhase=phase;
                // Rotate about the pelvis, not the feet: keep weight on the
                // mattress while swinging the legs over the long side.
                constexpr float hip=.39f;
                // Head-end surface (object 171) rises above the flat mattress.
                // Ease the lying support lift away before planting feet to stand.
                XMFLOAT3 center{-.37f,.25f+.03f*(1-sit)+.165f*stand,1.05f-.23f*swing-.30f*stand};
                XMFLOAT3 offset;XMStoreFloat3(&offset,XMVector3TransformNormal(XMVectorSet(0,hip,0,0),orientation(current)));
                current.position={center.x-offset.x,center.y-offset.y,center.z-offset.z};
                current.phone=step.target.clip==8?(t>=4.35f?1.f:0.f):(t<.75f?1.f:0.f);old=current;old.clip=previous.clip;
            }
            if(step.target.clip==11){
                current=mix(previous,step.target,smooth(t/.8f));current.clip=11;
                current.phone=t<.45f?1.f:0.f;old=current;old.clip=previous.clip;
            }
            if(step.target.clip==13){current.phone=t>.15f?1.f:0.f;}
            if(step.target.clip==12){current.phone=t<.45f?1.f:0.f;}
            if(step.target.clip==1){
                auto& r=route;float travelTime=t;
                float distance=.32f*(travelTime-.5f*r.rampIn);
                if(r.rampIn>0&&travelTime<r.rampIn){float u=travelTime/r.rampIn;distance=.32f*r.rampIn*(u*u*u-.5f*u*u*u*u);}
                if(r.rampOut>0&&travelTime>r.travel-r.rampOut){float u=(r.travel-travelTime)/r.rampOut;distance=r.distance-.32f*r.rampOut*(u*u*u-.5f*u*u*u*u);}
                distance=std::clamp(distance,0.f,r.distance);float u=r.parameter(distance);
                current=step.target;current.position=r.point(u);current.clip=1;
                float startYaw=r.tangent(0),pathYaw=startYaw+std::remainder(r.tangent(u)-startYaw,XM_2PI);
                current.yaw=pathYaw;
                if(previous.clip!=1){
                    // Unwrap once against the start tangent. Re-wrapping against
                    // a moving tangent flipped the turn at the +/- pi boundary.
                    float delta=std::remainder(startYaw-previous.yaw,XM_2PI);
                    float duration=std::min(r.travel*.80f,std::max(.65f,1.5f*fabsf(delta)/2.4f));
                    current.yaw=pathYaw-delta*(1-smooth(t/duration));
                }
                bool terminal=index+1==std::size(steps)||steps[index+1].target.clip!=1;
                if(terminal){
                    float endYaw=startYaw+std::remainder(r.tangent(1)-startYaw,XM_2PI);
                    float delta=std::remainder(step.target.yaw-endYaw,XM_2PI);
                    float duration=std::min(r.travel*.80f,std::max(.55f,1.5f*fabsf(delta)/2.4f));
                    current.yaw+=delta*smooth((t-r.travel+duration)/duration);
                }
                gait=(previous.clip==1?lastGait:0)+distance/.264f;
                // Look ahead by travelled distance, across adjoining curves.
                // A per-curve parameter offset jumped at every waypoint.
                float ahead=distance+.10f;size_t futureIndex=index;
                while(ahead>routes[futureIndex].distance&&futureIndex+1<std::size(steps)&&steps[futureIndex+1].target.clip==1){
                    ahead-=routes[futureIndex].distance;++futureIndex;
                }
                auto& future=routes[futureIndex];
                float futureYaw=future.tangent(future.parameter(std::min(ahead,future.distance)));
                // Keep the gaze on the body's chosen turn branch. Independently
                // selecting a shortest angle flips the head near a 180° turn.
                float futureUnwrapped=pathYaw+std::remainder(futureYaw-r.tangent(u),XM_2PI);
                look=gazeOffset(futureUnwrapped-current.yaw);
                // Settle the head before entering the next authored gesture.
                if(terminal)look*=smooth((r.travel-t)/.45f);
                old=current;old.clip=0;
                weight=(r.rampIn>0?smooth(t/r.rampIn):1)*(r.rampOut>0?smooth((r.travel-t)/r.rampOut):1);
                if(previous.clip!=1&&t<.28f){old.clip=previous.clip;weight=smooth(t/.28f);}
            }else if(index+1<std::size(steps)&&steps[index+1].target.clip==1){
                // Gaze leads the body during the last part of the preceding
                // gesture. The walking sample starts with this same target.
                auto& next=routes[index+1];
                float futureYaw=next.tangent(next.parameter(std::min(.10f,next.distance)));
                float startYaw=next.tangent(0);
                float turn=std::remainder(startYaw-current.yaw,XM_2PI)+std::remainder(futureYaw-startYaw,XM_2PI);
                look=gazeOffset(turn)*smooth((t-step.duration+.45f)/.45f);
            }
            bool tablePhone=step.tablePhone;
            if(step.target.clip==5)tablePhone=t>=1.8f;
            if(step.target.clip==6)tablePhone=t<1.8f;
            float walkTime=0,walkRemaining=0;
            if(current.clip==1){
                walkTime=t;walkRemaining=step.duration-t;
                for(size_t j=index;j>0&&steps[j-1].target.clip==1;--j)walkTime+=durations[j-1];
                for(size_t j=index+1;j<std::size(steps)&&steps[j].target.clip==1;++j)walkRemaining+=durations[j];
            }
            return {old,current,weight,t,tablePhone,gait,look,fromTime,walkTime,walkRemaining};
        }
        if(step.target.clip==1){lastGait=(previous.clip==1?lastGait:0)+route.distance/.264f;}
        t-=step.duration;previous=step.target;
    }
    return {};
}
inline Sample behaviour(double seconds){
    auto s=rawBehaviour(seconds);
    if(s.b.clip!=1)return s;
    // C1 path joins can still change angular velocity abruptly. Average the
    // body's heading in time across adjoining walking segments. Keep position,
    // cadence and contact animations intact, and preserve each endpoint pose.
    constexpr float weights[]={1,4,7,10,12,10,7,4,1};
    float delta=0;
    for(int i=0;i<9;i++){
        double offset=std::clamp((i-4)*.04,double(-s.walkTime)+1e-5,double(s.walkRemaining)-1e-5);
        auto nearby=rawBehaviour(seconds+offset);
        delta+=weights[i]*std::remainder(nearby.b.yaw-s.b.yaw,XM_2PI)/56.f;
    }
    float envelope=smooth(s.walkTime/.35f)*smooth(s.walkRemaining/.35f);
    delta*=envelope;
    s.b.yaw+=delta;s.a.yaw+=delta;
    // Preserve the direction of the gaze while the shoulders catch up.
    s.look-=delta;
    return s;
}
class Actor {
    ComPtr<ID3D11VertexShader> shader;ComPtr<ID3D11PixelShader> lighting;ComPtr<ID3D11InputLayout> layout;
    ComPtr<ID3D11Buffer> palette,transform;
    std::vector<Batch> batches;std::vector<Clip> clips;UINT boneCount=0;
    std::vector<UINT> secondary;
    double springTime=-1;float sway=0,swaySpeed=0,pitch=0,pitchSpeed=0,lastYaw=0,lastSpeed=0;
    XMFLOAT3 lastPosition{};
    void updateSecondary(double seconds,const Pose& p){
        double dt=seconds-springTime;
        if(springTime<0||dt<0||dt>.15){sway=swaySpeed=pitch=pitchSpeed=lastSpeed=0;}
        else if(dt>0){
            float speed=sqrtf(powf(p.position.x-lastPosition.x,2)+powf(p.position.z-lastPosition.z,2))/float(dt);
            float turn=std::remainder(p.yaw-lastYaw,XM_2PI)/float(dt);
            float targetYaw=std::clamp(-turn*.05f,-.16f,.16f);
            float targetPitch=std::clamp((speed-lastSpeed)/float(dt)*.012f,-.10f,.10f);
            int count=int(ceil(dt*120));float h=float(dt)/count;
            for(int i=0;i<count;i++){
                swaySpeed+=(70*(targetYaw-sway)-15*swaySpeed)*h;sway+=swaySpeed*h;
                pitchSpeed+=(95*(targetPitch-pitch)-18*pitchSpeed)*h;pitch+=pitchSpeed*h;
            }
            lastSpeed=speed;
        }
        springTime=seconds;lastYaw=p.yaw;lastPosition=p.position;
    }
    std::vector<int> parents;std::vector<UINT> boneOrder;std::vector<XMFLOAT4X4> inverseBind;
    template<class T>static T read(std::istream& f){T t{};read(f,&t,sizeof(t));return t;}
    static void read(std::istream& f,void* out,size_t n){if(!f.read(static_cast<char*>(out),n))throw std::runtime_error("Truncated actor");}
    static void check(HRESULT h){if(FAILED(h))throw std::runtime_error("Actor D3D resource failed");}
    XMFLOAT4X4 sample(int clip,UINT bone,float t) const {
        auto& c=clips.at(clip);float sampleTime=(clip==5||clip==6||clip==8||clip>=10)?std::clamp(t,0.f,c.duration):std::fmod(std::max(0.f,t),c.duration);
        float frame=sampleTime*(c.frames-1)/c.duration;
        UINT a=UINT(frame),b=std::min(a+1,c.frames-1);float w=frame-a;XMFLOAT4X4 result{};
        return blendRigid(c.matrices[size_t(a)*boneCount+bone],c.matrices[size_t(b)*boneCount+bone],w);
    }
public:
    bool ready()const{return !batches.empty();}
    void clear(){batches.clear();clips.clear();parents.clear();boneOrder.clear();inverseBind.clear();boneCount=0;secondary.clear();springTime=-1;shader.Reset();lighting.Reset();layout.Reset();palette.Reset();transform.Reset();}
    void load(ID3D11Device* device,const std::filesystem::path& path){
        clear();if(!std::filesystem::exists(path))return;
        std::ifstream f(path,std::ios::binary);char magic[8];read(f,magic,8);if(memcmp(magic,"DRMIKU3\0",8))throw std::runtime_error("Unknown actor format");
        boneCount=read<UINT>(f);UINT count=read<UINT>(f),clipCount=read<UINT>(f);
        if(!boneCount||boneCount>384||!count||count>128||clipCount!=14)throw std::runtime_error("Invalid actor header");
        parents.resize(boneCount);inverseBind.resize(boneCount);secondary.resize(boneCount);
        for(UINT i=0;i<boneCount;i++){parents[i]=read<int>(f);secondary[i]=read<UINT>(f);if(secondary[i]>2)throw std::runtime_error("Invalid secondary bone");inverseBind[i]=read<XMFLOAT4X4>(f);if(parents[i]<-1||parents[i]>=int(boneCount)||parents[i]==int(i))throw std::runtime_error("Invalid bone parent");}
        std::vector<bool> done(boneCount);
        while(boneOrder.size()<boneCount){auto before=boneOrder.size();for(UINT i=0;i<boneCount;i++)if(!done[i]&&(parents[i]<0||done[parents[i]])){done[i]=true;boneOrder.push_back(i);}if(before==boneOrder.size())throw std::runtime_error("Cyclic skeleton");}
        for(UINT i=0;i<count;i++){
            Batch batch{};batch.count=read<UINT>(f);UINT w=read<UINT>(f),h=read<UINT>(f);
            if(!batch.count||batch.count>1000000||batch.count%3||!w||!h||w>4096||h>4096)throw std::runtime_error("Invalid actor mesh");
            std::vector<Vertex> vertices(batch.count);read(f,vertices.data(),vertices.size()*sizeof(Vertex));
            for(auto& v:vertices){float sum=0;for(int j=0;j<4;j++){if(v.bone[j]>=boneCount||!std::isfinite(v.weight[j])||v.weight[j]<0)throw std::runtime_error("Invalid skin weight");sum+=v.weight[j];}if(std::abs(sum-1)>1e-4f)throw std::runtime_error("Skin weights not normalized");}
            D3D11_BUFFER_DESC bd{};bd.ByteWidth=UINT(vertices.size()*sizeof(Vertex));bd.Usage=D3D11_USAGE_IMMUTABLE;bd.BindFlags=D3D11_BIND_VERTEX_BUFFER;
            D3D11_SUBRESOURCE_DATA data{vertices.data(),0,0};check(device->CreateBuffer(&bd,&data,&batch.vertices));
            std::vector<unsigned char> rgba(size_t(w)*h*4);read(f,rgba.data(),rgba.size());
            D3D11_TEXTURE2D_DESC td{};td.Width=w;td.Height=h;td.MipLevels=td.ArraySize=1;td.Format=DXGI_FORMAT_R8G8B8A8_UNORM;td.SampleDesc.Count=1;td.Usage=D3D11_USAGE_IMMUTABLE;td.BindFlags=D3D11_BIND_SHADER_RESOURCE;
            data={rgba.data(),w*4,0};ComPtr<ID3D11Texture2D> tex;check(device->CreateTexture2D(&td,&data,&tex));check(device->CreateShaderResourceView(tex.Get(),nullptr,&batch.texture));batches.push_back(std::move(batch));
        }
        for(UINT i=0;i<clipCount;i++){
            Clip clip;char name[32]{};read(f,name,32);clip.name=std::string(name,strnlen(name,32));clip.frames=read<UINT>(f);clip.duration=read<float>(f);
            if(clip.frames<2||clip.frames>1801||!std::isfinite(clip.duration)||clip.duration<=0||clip.duration>60)throw std::runtime_error("Invalid actor clip");
            clip.matrices.resize(size_t(clip.frames)*boneCount);read(f,clip.matrices.data(),clip.matrices.size()*sizeof(XMFLOAT4X4));
            for(auto& m:clip.matrices)for(float v:std::array<float,16>{m._11,m._12,m._13,m._14,m._21,m._22,m._23,m._24,m._31,m._32,m._33,m._34,m._41,m._42,m._43,m._44})if(!std::isfinite(v))throw std::runtime_error("Invalid pose matrix");
            clips.push_back(std::move(clip));
        }
        const char* source=R"(
cbuffer Params:register(b0){row_major float4x4 mvp;float4 a;float4 b;};
cbuffer Skin:register(b1){row_major float4x4 bones[384];};
struct V{float3 p:POSITION;float3 n:NORMAL;float2 uv:TEXCOORD0;uint4 ids:BLENDINDICES;float4 w:BLENDWEIGHT;};
struct P{float4 p:SV_POSITION;float3 n:NORMAL;float2 uv:TEXCOORD0;float3 world:TEXCOORD1;};
P main(V v){float4 p=0;float3 n=0;[unroll]for(int i=0;i<4;i++){p+=mul(float4(v.p,1),bones[v.ids[i]])*v.w[i];n+=mul(float4(v.n,0),bones[v.ids[i]]).xyz*v.w[i];}P o;o.p=mul(p,mvp);o.n=n;o.uv=v.uv;o.world=p.xyz;return o;})";
        ComPtr<ID3DBlob> code,error;check(D3DCompile(source,strlen(source),"RoomActor",nullptr,nullptr,"main","vs_5_0",D3DCOMPILE_ENABLE_STRICTNESS,0,&code,&error));
        shader.Reset();layout.Reset();palette.Reset();transform.Reset();
        check(device->CreateVertexShader(code->GetBufferPointer(),code->GetBufferSize(),nullptr,&shader));
        // Interim room lighting; this is not the game's Mega Mix / Future Tone shader.
        const char* pixelSource=R"(
Texture2D tex:register(t0);SamplerState smp:register(s0);
struct P{float4 p:SV_POSITION;float3 n:NORMAL;float2 uv:TEXCOORD0;float3 world:TEXCOORD1;};
float4 main(P p):SV_TARGET{
 float4 color=tex.Sample(smp,p.uv);clip(color.a-.2);
 float3 n=normalize(p.n);float3 toLight=float3(0,1.8,0)-p.world;
 float key=saturate(dot(n,normalize(toLight)))/(1+.08*dot(toLight,toLight));
 float3 light=.86+.17*key;
 return float4(saturate(color.rgb*light),1);
})";
        ComPtr<ID3DBlob> pixel;check(D3DCompile(pixelSource,strlen(pixelSource),"RoomActorLight",nullptr,nullptr,"main","ps_5_0",D3DCOMPILE_ENABLE_STRICTNESS,0,&pixel,&error));
        lighting.Reset();check(device->CreatePixelShader(pixel->GetBufferPointer(),pixel->GetBufferSize(),nullptr,&lighting));
        D3D11_INPUT_ELEMENT_DESC elements[]={{"POSITION",0,DXGI_FORMAT_R32G32B32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0},{"NORMAL",0,DXGI_FORMAT_R32G32B32_FLOAT,0,12,D3D11_INPUT_PER_VERTEX_DATA,0},{"TEXCOORD",0,DXGI_FORMAT_R32G32_FLOAT,0,24,D3D11_INPUT_PER_VERTEX_DATA,0},{"BLENDINDICES",0,DXGI_FORMAT_R32G32B32A32_UINT,0,32,D3D11_INPUT_PER_VERTEX_DATA,0},{"BLENDWEIGHT",0,DXGI_FORMAT_R32G32B32A32_FLOAT,0,48,D3D11_INPUT_PER_VERTEX_DATA,0}};
        check(device->CreateInputLayout(elements,5,code->GetBufferPointer(),code->GetBufferSize(),&layout));
        D3D11_BUFFER_DESC cb{};cb.ByteWidth=384*sizeof(XMFLOAT4X4);cb.Usage=D3D11_USAGE_DEFAULT;cb.BindFlags=D3D11_BIND_CONSTANT_BUFFER;check(device->CreateBuffer(&cb,nullptr,&palette));cb.ByteWidth=96;check(device->CreateBuffer(&cb,nullptr,&transform));
    }
    void camera(double seconds,XMFLOAT3& eye,XMFLOAT3& at)const{
        if(!ready())return;auto s=behaviour(seconds);auto p=s.b;
        XMFLOAT3 target{p.position.x-.34f*p.recline,p.position.y+.40f*(1-p.recline),p.position.z};
        // The camera remains within the room and looks toward Miku from its front side.
        at=target;eye={std::clamp(target.x-.45f*(1-p.recline),-1.05f,.75f),1.10f,target.z+1.25f};eye.z=std::min(eye.z,1.70f);
        auto seatedAmount=[](int clip,float time){
            if(clip==11)return smooth((time-.8f)/1.6f);
            if(clip==12)return 1-smooth((time-.55f)/1.65f);
            return (clip==7||clip==13)?1.f:0.f;
        };
        float seated=seatedAmount(s.a.clip,s.a.clip>=10?clips[s.a.clip].duration:s.local)*(1-s.weight)+seatedAmount(s.b.clip,s.local)*s.weight;
        eye={eye.x+(.85f-eye.x)*seated,eye.y+(.65f-eye.y)*seated,eye.z+(-.05f-eye.z)*seated};
        at.y+=(.34f-at.y)*seated;
    }
    void draw(ID3D11DeviceContext* c,FXMMATRIX viewProjection,double seconds){
        if(!ready())return;auto s=behaviour(seconds);auto p=s.b;
        updateSecondary(seconds,p);
        std::array<XMFLOAT4X4,384> matrices{};
        // Contact is authored at the actual table height; never lift the root
        // to make the phone reach, which would also lift both planted feet.
        auto world=XMMatrixScaling(.44f,.44f,.44f)*orientation(p)*XMMatrixTranslation(p.position.x,p.position.y,p.position.z);
        std::array<XMFLOAT4X4,384> globalPose{};
        for(UINT bone:boneOrder){
            auto a=sample(s.a.clip,bone,s.fromTime>=0?s.fromTime:s.a.clip==9?1.f:s.a.clip==1?s.gait:(s.a.clip==5||s.a.clip==6||s.a.clip==8||s.a.clip>=10)?clips[s.a.clip].duration:s.local);
            auto b=sample(s.b.clip,bone,(s.b.clip==1||s.b.clip==9)?s.gait:s.local);a=blendRigid(a,b,s.weight);
            auto pose=XMLoadFloat4x4(&a);
            if(s.look!=0&&(bone==RoomActorBones::Head||bone==RoomActorBones::Torso)){
                auto axis=bone==RoomActorBones::Head?RoomActorBones::HeadAxis:RoomActorBones::TorsoAxis;
                auto translation=pose.r[3];
                pose=pose*XMMatrixRotationAxis(XMVectorSet(axis[0],axis[1],axis[2],0),s.look*(bone==RoomActorBones::Head?.65f:.35f));
                pose.r[3]=translation;
            }
            if(secondary[bone]){
                float gain=secondary[bone]==2?.45f:.25f;
                float attenuation=1-p.recline*.85f;
                pose=XMMatrixRotationX(pitch*gain*attenuation)*XMMatrixRotationZ(sway*gain*attenuation)*pose;
            }
            if(parents[bone]>=0)pose=pose*XMLoadFloat4x4(&globalPose[parents[bone]]);
            XMStoreFloat4x4(&globalPose[bone],pose);
            auto m=XMLoadFloat4x4(&inverseBind[bone])*pose*world;
            if(bone==boneCount-1){
                if(s.tablePhone)m=XMMatrixScaling(.44f,.44f,.44f)*XMMatrixRotationY(-XM_PIDIV2)*XMMatrixTranslation(.43f,.317f,-.32f);
                else if(p.phone<.5f)m=XMMatrixScaling(0,0,0);
            }
            XMStoreFloat4x4(&matrices[bone],m);
        }
        struct Params{XMFLOAT4X4 m;float rest[8]{};}params{};XMStoreFloat4x4(&params.m,viewProjection);
        c->UpdateSubresource(transform.Get(),0,nullptr,&params,0,0);c->UpdateSubresource(palette.Get(),0,nullptr,matrices.data(),0,0);
        auto* cb=transform.Get();c->VSSetConstantBuffers(0,1,&cb);c->PSSetConstantBuffers(0,1,&cb);cb=palette.Get();c->VSSetConstantBuffers(1,1,&cb);
        c->VSSetShader(shader.Get(),nullptr,0);c->PSSetShader(lighting.Get(),nullptr,0);c->IASetInputLayout(layout.Get());
        for(auto& b:batches){auto* vb=b.vertices.Get();UINT stride=sizeof(Vertex),offset=0;c->IASetVertexBuffers(0,1,&vb,&stride,&offset);auto* tex=b.texture.Get();c->PSSetShaderResources(0,1,&tex);c->Draw(b.count,0);}
    }
};
}




