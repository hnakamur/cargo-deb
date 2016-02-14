// Copyright © 2015; Connor Hilarides
// Licensed under the MIT License <LICENSE.md>
//! Mappings for the contents of dxgitype.h
pub const DXGI_CPU_ACCESS_NONE: ::DWORD = 0;
pub const DXGI_CPU_ACCESS_DYNAMIC: ::DWORD = 1;
pub const DXGI_CPU_ACCESS_READ_WRITE: ::DWORD = 2;
pub const DXGI_CPU_ACCESS_SCRATCH: ::DWORD = 3;
pub const DXGI_CPU_ACCESS_FIELD: ::DWORD = 15;
FLAGS!{enum DXGI_USAGE {
    DXGI_USAGE_SHADER_INPUT = 1 << (0 + 4),
    DXGI_USAGE_RENDER_TARGET_OUTPUT = 1 << (1 + 4),
    DXGI_USAGE_BACK_BUFFER = 1 << (2 + 4),
    DXGI_USAGE_SHARED = 1 << (3 + 4),
    DXGI_USAGE_READ_ONLY = 1 << (4 + 4),
    DXGI_USAGE_DISCARD_ON_PRESENT = 1 << (5 + 4),
    DXGI_USAGE_UNORDERED_ACCESS = 1 << (6 + 4),
}}
STRUCT!{struct DXGI_RGB {
    Red: f32,
    Green: f32,
    Blue: f32,
}}
pub type DXGI_RGBA = ::D3DCOLORVALUE;
#[repr(C)] #[derive(Copy)]
pub struct DXGI_GAMMA_CONTROL {
    pub Scale: DXGI_RGB,
    pub Offset: DXGI_RGB,
    pub GammaCurve: [DXGI_RGB; 1025],
}
impl Clone for DXGI_GAMMA_CONTROL {
    fn clone(&self) -> DXGI_GAMMA_CONTROL {
        *self
    }
}
#[repr(C)] #[derive(Copy)]
pub struct DXGI_GAMMA_CONTROL_CAPABILITIES {
    pub ScaleAndOffsetSupported: ::BOOL,
    pub MaxConvertedValue: f32,
    pub MinConvertedValue: f32,
    pub NumGammaControlPoints: ::UINT,
    pub ControlPointPositions: [f32; 1025],
}
impl Clone for DXGI_GAMMA_CONTROL_CAPABILITIES {
    fn clone(&self) -> DXGI_GAMMA_CONTROL_CAPABILITIES {
        *self
    }
}
STRUCT!{struct DXGI_RATIONAL {
    Numerator: ::UINT,
    Denominator: ::UINT,
}}
ENUM!{enum DXGI_MODE_SCANLINE_ORDER {
    DXGI_MODE_SCANLINE_ORDER_UNSPECIFIED,
    DXGI_MODE_SCANLINE_ORDER_PROGRESSIVE,
    DXGI_MODE_SCANLINE_ORDER_UPPER_FIELD_FIRST,
    DXGI_MODE_SCANLINE_ORDER_LOWER_FIELD_FIRST,
}}
ENUM!{enum DXGI_MODE_SCALING {
    DXGI_MODE_SCALING_UNSPECIFIED,
    DXGI_MODE_SCALING_CENTERED,
    DXGI_MODE_SCALING_STRETCHED,
}}
ENUM!{enum DXGI_MODE_ROTATION {
    DXGI_MODE_ROTATION_UNSPECIFIED,
    DXGI_MODE_ROTATION_IDENTITY,
    DXGI_MODE_ROTATION_ROTATE90,
    DXGI_MODE_ROTATION_ROTATE180,
    DXGI_MODE_ROTATION_ROTATE270,
}}
STRUCT!{struct DXGI_MODE_DESC {
    Width: ::UINT,
    Height: ::UINT,
    RefreshRate: DXGI_RATIONAL,
    Format: ::DXGI_FORMAT,
    ScanlineOrdering: DXGI_MODE_SCANLINE_ORDER,
    Scaling: DXGI_MODE_SCALING,
}}
STRUCT!{struct DXGI_SAMPLE_DESC {
    Count: ::UINT,
    Quality: ::UINT,
}}
ENUM!{enum DXGI_COLOR_SPACE_TYPE {
    DXGI_COLOR_SPACE_RGB_FULL_G22_NONE_P709 = 0x0,
    DXGI_COLOR_SPACE_RGB_FULL_G10_NONE_P709 = 0x1,
    DXGI_COLOR_SPACE_RGB_STUDIO_G22_NONE_P709 = 0x2,
    DXGI_COLOR_SPACE_RGB_STUDIO_G22_NONE_P2020 = 0x3,
    DXGI_COLOR_SPACE_RESERVED = 0x4,
    DXGI_COLOR_SPACE_YCBCR_FULL_G22_NONE_P709_X601 = 0x5,
    DXGI_COLOR_SPACE_YCBCR_STUDIO_G22_LEFT_P601 = 0x6,
    DXGI_COLOR_SPACE_YCBCR_FULL_G22_LEFT_P601 = 0x7,
    DXGI_COLOR_SPACE_YCBCR_STUDIO_G22_LEFT_P709 = 0x8,
    DXGI_COLOR_SPACE_YCBCR_FULL_G22_LEFT_P709 = 0x9,
    DXGI_COLOR_SPACE_YCBCR_STUDIO_G22_LEFT_P2020 = 0xA,
    DXGI_COLOR_SPACE_YCBCR_FULL_G22_LEFT_P2020 = 0xB,
    DXGI_COLOR_SPACE_CUSTOM = 0xFFFFFFFF,
}}
pub const DXGI_CENTER_MULTISAMPLE_QUALITY_PATTERN: ::UINT = 0xfffffffe;
pub const DXGI_STANDARD_MULTISAMPLE_QUALITY_PATTERN: ::UINT = 0xffffffff;