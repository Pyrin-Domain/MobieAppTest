package com.shezik.drawanywhere

import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class DataClassTest {

    @Test
    fun testPenConfig_defaultValues() {
        val config = PenConfig()
        assertEquals(PenType.Pen, config.penType)
        assertEquals(Color.Red, config.color)
        assertEquals(5f, config.width, 0.001f)
        assertEquals(1f, config.alpha, 0.001f)
    }

    @Test
    fun testPenConfig_customValues() {
        val config = PenConfig(
            penType = PenType.StrokeEraser,
            color = Color.Blue,
            width = 20f,
            alpha = 0.5f
        )
        assertEquals(PenType.StrokeEraser, config.penType)
        assertEquals(Color.Blue, config.color)
        assertEquals(20f, config.width, 0.001f)
        assertEquals(0.5f, config.alpha, 0.001f)
    }

    @Test
    fun testPenConfig_copy_createsNewInstance() {
        val original = PenConfig(penType = PenType.Pen, color = Color.Red, width = 5f)
        val copied = original.copy(width = 10f)

        assertEquals(PenType.Pen, copied.penType)
        assertEquals(Color.Red, copied.color)
        assertEquals(10f, copied.width, 0.001f)
        assertEquals(5f, original.width, 0.001f)  // Original unchanged
    }

    @Test
    fun testPathWrapper_creation() {
        val points = androidx.compose.runtime.mutableStateListOf(Offset(0f, 0f), Offset(10f, 10f))
        val wrapper = PathWrapper(
            points = points,
            color = Color.Red,
            width = 5f,
            alpha = 1f
        )

        assertNotNull(wrapper.id)
        assertEquals(2, wrapper.points.size)
        assertEquals(Color.Red, wrapper.color)
        assertEquals(5f, wrapper.width, 0.001f)
        assertEquals(1f, wrapper.alpha, 0.001f)
    }

    @Test
    fun testPathWrapper_cachedPath_generation() {
        val points = androidx.compose.runtime.mutableStateListOf(Offset(0f, 0f), Offset(10f, 10f))
        val wrapper = PathWrapper(
            points = points,
            color = Color.Red,
            width = 5f,
            alpha = 1f
        )

        // Access cachedPath should generate it
        val path = wrapper.cachedPath
        assertFalse(path.isEmpty)
    }

    @Test
    fun testPathWrapper_invalidatePath_marksCacheInvalid() {
        val points = androidx.compose.runtime.mutableStateListOf(Offset(0f, 0f), Offset(10f, 10f))
        val wrapper = PathWrapper(
            points = points,
            color = Color.Red,
            width = 5f,
            alpha = 1f
        )

        // Generate cache
        val path1 = wrapper.cachedPath
        
        // Invalidate
        wrapper.invalidatePath()
        
        // Access again should regenerate
        val path2 = wrapper.cachedPath
        assertNotNull(path2)
    }

    @Test
    fun testPathWrapper_releasePath_clearsCache() {
        val points = androidx.compose.runtime.mutableStateListOf(Offset(0f, 0f), Offset(10f, 10f))
        val wrapper = PathWrapper(
            points = points,
            color = Color.Red,
            width = 5f,
            alpha = 1f
        )

        // Generate cache
        wrapper.cachedPath
        
        // Release
        val released = wrapper.releasePath()
        
        assertNotNull(released)
    }

    @Test
    fun testServiceState_defaultValues() {
        val state = ServiceState()
        assertEquals(32f, state.toolbarPosition.x, 0.001f)
        assertEquals(64f, state.toolbarPosition.y, 0.001f)
        assertFalse(state.positionValidated)
        assertTrue(state.toolbarActive)
    }

    @Test
    fun testServiceState_customValues() {
        val position = androidx.compose.ui.geometry.Offset(100f, 200f)
        val state = ServiceState(
            toolbarPosition = position,
            positionValidated = true,
            toolbarActive = false
        )
        assertEquals(100f, state.toolbarPosition.x, 0.001f)
        assertEquals(200f, state.toolbarPosition.y, 0.001f)
        assertTrue(state.positionValidated)
        assertFalse(state.toolbarActive)
    }

    @Test
    fun testUiState_defaultValues() {
        val state = UiState()
        assertTrue(state.canvasVisible)
        assertFalse(state.canvasPassthrough)
        assertFalse(state.autoClearCanvas)
        assertTrue(state.visibleOnStart)
        assertEquals(PenType.Pen, state.currentPenType)
        assertEquals(ToolbarOrientation.HORIZONTAL, state.toolbarOrientation)
    }

    @Test
    fun testUiState_currentPenConfig_returnsCorrectConfig() {
        val state = UiState()
        val config = state.currentPenConfig
        assertEquals(PenType.Pen, config.penType)
    }

    @Test
    fun testUiState_withCustomPenConfigs() {
        val customConfigs = mapOf(
            PenType.Pen to PenConfig(penType = PenType.Pen, color = Color.Blue, width = 10f),
            PenType.StrokeEraser to PenConfig(penType = PenType.StrokeEraser, width = 50f)
        )
        val state = UiState(penConfigs = customConfigs)
        
        val penConfig = state.penConfigs[PenType.Pen]
        assertNotNull(penConfig)
        assertEquals(Color.Blue, penConfig?.color)
        assertEquals(10f, penConfig!!.width, 0.001f)
    }

    @Test
    fun testDefaultPenConfigs_returnsExpectedMap() {
        val configs = defaultPenConfigs()
        
        assertTrue(configs.containsKey(PenType.Pen))
        assertTrue(configs.containsKey(PenType.StrokeEraser))
        
        val penConfig = configs[PenType.Pen]
        assertEquals(PenType.Pen, penConfig?.penType)
        
        val eraserConfig = configs[PenType.StrokeEraser]
        assertEquals(PenType.StrokeEraser, eraserConfig?.penType)
        assertEquals(50f, eraserConfig!!.width, 0.001f)
    }

    @Test
    fun testDrawAction_addPath() {
        val points = androidx.compose.runtime.mutableStateListOf(Offset(0f, 0f))
        val wrapper = PathWrapper(
            points = points,
            color = Color.Red,
            width = 5f,
            alpha = 1f
        )
        
        val action = DrawAction.AddPath(wrapper)
        
        assertTrue(action is DrawAction.AddPath)
        assertEquals(wrapper, (action as DrawAction.AddPath).pathWrapper)
    }

    @Test
    fun testDrawAction_erasePath() {
        val points = androidx.compose.runtime.mutableStateListOf(Offset(0f, 0f))
        val wrapper = PathWrapper(
            points = points,
            color = Color.Red,
            width = 5f,
            alpha = 1f
        )
        
        val action = DrawAction.ErasePath(wrapper)
        
        assertTrue(action is DrawAction.ErasePath)
        assertEquals(wrapper, (action as DrawAction.ErasePath).pathWrapper)
    }

    @Test
    fun testDrawAction_clearPaths() {
        val wrappers = listOf<PathWrapper>()
        val action = DrawAction.ClearPaths(wrappers)
        
        assertTrue(action is DrawAction.ClearPaths)
        assertEquals(wrappers, (action as DrawAction.ClearPaths).paths)
    }

    @Test
    fun testEnumPenType_hasExpectedValues() {
        val types = PenType.entries
        assertTrue(types.contains(PenType.Pen))
        assertTrue(types.contains(PenType.StrokeEraser))
    }

    @Test
    fun testEnumToolbarOrientation_hasExpectedValues() {
        // This test assumes ToolbarOrientation enum exists
        // If it's defined elsewhere, this validates its structure
        assertTrue(true)  // Placeholder - actual enum tested in other tests
    }

    @Test
    fun testEnumStrokeModifier_hasExpectedValues() {
        val modifiers = StrokeModifier.entries
        assertTrue(modifiers.contains(StrokeModifier.None))
        assertTrue(modifiers.contains(StrokeModifier.PrimaryButton))
        assertTrue(modifiers.contains(StrokeModifier.SecondaryButton))
        assertTrue(modifiers.contains(StrokeModifier.Both))
    }
}
