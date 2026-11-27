#pragma once
#include <Windows.h>
#include <d3d11.h>
#include <dxgi.h>

namespace RoomView {
// Only called on the game's update thread. Rendering never invokes game APIs.
struct LoadingApi {
    bool (*begin)();
    void (*finish)();
    bool (*finished)();
    void (*reset)();
    void (*leaveMenu)();
    void (*returnMenu)();
    void (*sound)(int); // 0 confirm, 1 cancel, 2 selection, 3 pause open
    bool (*menuExited)();
    bool (*startMusic)();
    void (*updateMusic)();
    void (*stopMusic)();
};
enum class Action { Pause, Up, Down, Accept, Cancel };
void Act(Action action);
bool IsPaused();
bool ReleaseScene();
void SetLoadingApi(LoadingApi api);
// Native actions are press events already; do not edge-filter them again.
void SetInputReader(unsigned (*pressed)());
void Update();
void SetModule(HMODULE module);
void Initialize(IDXGISwapChain* swap, ID3D11Device* device, ID3D11DeviceContext* context);
void Open();
bool BlocksMenu();
void Frame(IDXGISwapChain* swap);
void UseNativeRenderPass();
bool HasRoomVisuals();
// Called by the game's command executor on its actual D3D context/target.
void RenderNative(ID3D11DeviceContext* context);
void Resized();
}
