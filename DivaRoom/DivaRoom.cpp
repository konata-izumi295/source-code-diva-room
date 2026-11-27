#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <atomic>
#include "NativeMenu.h"
#include "NativeRender.h"

// The native adapter validates the executable and every patch site before
// enabling the seven-entry menu and custom character through DivaModLoader.
namespace DivaRoom {
    std::atomic<bool> initialized{false};
    constexpr int TotalOptions = 7;
    constexpr int OriginalOptions = 6;

    constexpr int ToOriginalIndex(int index) {
        if (index < 0 || index >= TotalOptions || index == 1) return -1;
        return index > 1 ? index - 1 : index;
    }
    constexpr int ToNewIndex(int index) {
        if (index < 0 || index >= OriginalOptions) return -1;
        return index == 0 ? 0 : index + 1;
    }
    constexpr bool ValidMenuMapping() {
        if (ToOriginalIndex(1) != -1) return false;
        for (int i = 0; i < OriginalOptions; ++i)
            if (ToOriginalIndex(ToNewIndex(i)) != i) return false;
        return true;
    }
    static_assert(ValidMenuMapping());
}

extern "C" __declspec(dllexport) void Init() {
    if (!DivaRoom::initialized.exchange(true)) {
        NativeMenu::Install();
        NativeRender::Install(reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr)));
    }
}

// These callbacks render the actual room mesh; they do not write diagnostics.
extern "C" __declspec(dllexport) void D3DInit(IDXGISwapChain* swap, ID3D11Device* device, ID3D11DeviceContext* context) {
    RoomView::Initialize(swap,device,context);
}
extern "C" __declspec(dllexport) void OnFrame(IDXGISwapChain* swap) {
    RoomView::Frame(swap);
}
extern "C" __declspec(dllexport) void OnResize(IDXGISwapChain*) {
    RoomView::Resized();
}

// Retain existing query exports for tools that inspect the menu adapter.
extern "C" __declspec(dllexport) int DivaRoom_ToOriginalIndex(int index) {
    return DivaRoom::ToOriginalIndex(index);
}
extern "C" __declspec(dllexport) int DivaRoom_ToNewIndex(int index) {
    return DivaRoom::ToNewIndex(index);
}
extern "C" __declspec(dllexport) int DivaRoom_GetOptionCount() {
    return DivaRoom::TotalOptions;
}

BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        RoomView::SetModule(module);
        DisableThreadLibraryCalls(module);
    }
    return TRUE;
}
