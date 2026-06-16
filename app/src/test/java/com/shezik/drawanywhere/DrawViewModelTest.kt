package com.shezik.drawanywhere

import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import io.mockk.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.test.*
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class DrawViewModelTest {

    private lateinit var viewModel: DrawViewModel
    private lateinit var mockController: DrawController
    private lateinit var mockPreferencesMgr: PreferencesManager
    private var serviceStopped = false

    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        
        mockController = mockk(relaxed = true)
        mockPreferencesMgr = mockk(relaxed = true)
        serviceStopped = false

        val initialUiState = UiState()
        val initialServiceState = ServiceState()

        viewModel = DrawViewModel(
            controller = mockController,
            preferencesMgr = mockPreferencesMgr,
            initialUiState = initialUiState,
            initialServiceState = initialServiceState,
            stopService = { serviceStopped = true }
        )
    }

    @Test
    fun testInitialState_valuesAreCorrect() = runBlocking {
        assertEquals(true, viewModel.uiState.value.canvasVisible)
        assertEquals(false, viewModel.uiState.value.canvasPassthrough)
        assertEquals(PenType.Pen, viewModel.uiState.value.currentPenType)
    }

    @Test
    fun testSwitchToPen_changesPenType() = runBlocking {
        // When
        viewModel.switchToPen(PenType.StrokeEraser)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertEquals(PenType.StrokeEraser, viewModel.uiState.value.currentPenType)
    }

    @Test
    fun testSetPenColor_updatesPenConfig() = runBlocking {
        // Given
        val newColor = Color.Blue
        val initialConfig = viewModel.uiState.value.currentPenConfig

        // When
        viewModel.setPenColor(newColor)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        val updatedConfig = viewModel.uiState.value.penConfigs[PenType.Pen]
        assertNotNull(updatedConfig)
        assertEquals(newColor, updatedConfig?.color)
    }

    @Test
    fun testSetStrokeWidth_updatesPenConfig() = runBlocking {
        // Given
        val newWidth = 20f

        // When
        viewModel.setStrokeWidth(newWidth)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        val updatedConfig = viewModel.uiState.value.penConfigs[PenType.Pen]
        assertNotNull(updatedConfig)
        assertEquals(newWidth, updatedConfig?.width)
    }

    @Test
    fun testSetStrokeAlpha_updatesPenConfig() = runBlocking {
        // Given
        val newAlpha = 0.5f

        // When
        viewModel.setStrokeAlpha(newAlpha)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        val updatedConfig = viewModel.uiState.value.penConfigs[PenType.Pen]
        assertNotNull(updatedConfig)
        assertEquals(newAlpha, updatedConfig?.alpha)
    }

    @Test
    fun testToggleCanvasVisibility_togglesVisibility() = runBlocking {
        // Given
        assertTrue(viewModel.uiState.value.canvasVisible)

        // When
        viewModel.toggleCanvasVisibility()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertFalse(viewModel.uiState.value.canvasVisible)

        // When - toggle again
        viewModel.toggleCanvasVisibility()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.uiState.value.canvasVisible)
    }

    @Test
    fun testSetCanvasVisibility_hidesCanvas() = runBlocking {
        // When
        viewModel.setCanvasVisibility(false)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertFalse(viewModel.uiState.value.canvasVisible)
    }

    @Test
    fun testToggleCanvasPassthrough_togglesPassthrough() = runBlocking {
        // Given
        assertFalse(viewModel.uiState.value.canvasPassthrough)

        // When
        viewModel.toggleCanvasPassthrough()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.uiState.value.canvasPassthrough)
    }

    @Test
    fun testSetCanvasPassthrough_setsPassthrough() = runBlocking {
        // When
        viewModel.setCanvasPassthrough(true)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.uiState.value.canvasPassthrough)
    }

    @Test
    fun testClearCanvas_callsController() = runBlocking {
        // When
        viewModel.clearCanvas()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        verify { mockController.clearPaths() }
    }

    @Test
    fun testUndo_callsController() = runBlocking {
        // When
        viewModel.undo()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        verify { mockController.undo() }
    }

    @Test
    fun testRedo_callsController() = runBlocking {
        // When
        viewModel.redo()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        verify { mockController.redo() }
    }

    @Test
    fun testSetToolbarPosition_updatesServiceState() = runBlocking {
        // Given
        val newPosition = Offset(100f, 200f)

        // When
        viewModel.setToolbarPosition(newPosition)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertEquals(newPosition, viewModel.serviceState.value.toolbarPosition)
    }

    @Test
    fun testUpdateToolbarPosition_offsetsPosition() = runBlocking {
        // Given
        val initialPosition = viewModel.serviceState.value.toolbarPosition
        val offset = Offset(50f, 50f)

        // When
        viewModel.updateToolbarPosition(offset)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertEquals(initialPosition + offset, viewModel.serviceState.value.toolbarPosition)
    }

    @Test
    fun testToggleToolbarOrientation_togglesOrientation() = runBlocking {
        // Given
        assertEquals(ToolbarOrientation.HORIZONTAL, viewModel.uiState.value.toolbarOrientation)

        // When
        viewModel.toggleToolbarOrientation()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertEquals(ToolbarOrientation.VERTICAL, viewModel.uiState.value.toolbarOrientation)

        // When - toggle again
        viewModel.toggleToolbarOrientation()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertEquals(ToolbarOrientation.HORIZONTAL, viewModel.uiState.value.toolbarOrientation)
    }

    @Test
    fun testSetToolbarOrientation_setsOrientation() = runBlocking {
        // When
        viewModel.setToolbarOrientation(ToolbarOrientation.VERTICAL)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertEquals(ToolbarOrientation.VERTICAL, viewModel.uiState.value.toolbarOrientation)
    }

    @Test
    fun testToggleFirstDrawer_togglesDrawer() = runBlocking {
        // Given
        assertTrue(viewModel.uiState.value.firstDrawerOpen)

        // When
        viewModel.toggleFirstDrawer()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertFalse(viewModel.uiState.value.firstDrawerOpen)
    }

    @Test
    fun testSetFirstDrawerOpen_setsDrawerState() = runBlocking {
        // When
        viewModel.setFirstDrawerOpen(false)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertFalse(viewModel.uiState.value.firstDrawerOpen)
    }

    @Test
    fun testToggleSecondDrawer_togglesDrawer() = runBlocking {
        // Given
        assertFalse(viewModel.uiState.value.secondDrawerOpen)

        // When
        viewModel.toggleSecondDrawer()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.uiState.value.secondDrawerOpen)
    }

    @Test
    fun testSetSecondDrawerOpen_setsDrawerState() = runBlocking {
        // When
        viewModel.setSecondDrawerOpen(true)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.uiState.value.secondDrawerOpen)
    }

    @Test
    fun testPinSecondDrawerButton_pinsButton() = runBlocking {
        // When
        viewModel.pinSecondDrawerButton("passthrough", true)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))
    }

    @Test
    fun testToggleSecondDrawerPinned_togglesPin() = runBlocking {
        // Given
        assertFalse(viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))

        // When
        viewModel.toggleSecondDrawerPinned("passthrough")
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))

        // When - toggle again
        viewModel.toggleSecondDrawerPinned("passthrough")
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertFalse(viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))
    }

    @Test
    fun testSetAutoClearCanvas_setsAutoClear() = runBlocking {
        // When
        viewModel.setAutoClearCanvas(true)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.uiState.value.autoClearCanvas)
    }

    @Test
    fun testSetVisibleOnStart_setsVisibleOnStart() = runBlocking {
        // When
        viewModel.setVisibleOnStart(false)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertFalse(viewModel.uiState.value.visibleOnStart)
    }

    @Test
    fun testQuitApplication_stopsService() = runBlocking {
        // When
        viewModel.quitApplication()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(serviceStopped)
        coVerify { mockPreferencesMgr.saveUiState(any()) }
        coVerify { mockPreferencesMgr.saveServiceState(any()) }
    }

    @Test
    fun testStartStroke_createsPath() = runBlocking {
        // Given
        val point = Offset(10f, 20f)

        // When
        viewModel.startStroke(point, StrokeModifier.None)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        verify { mockController.createPath(point) }
        assertTrue(viewModel.isStrokeDown)
    }

    @Test
    fun testUpdateStroke_updatesPath() = runBlocking {
        // Given
        viewModel.startStroke(Offset(10f, 20f), StrokeModifier.None)
        val point = Offset(30f, 40f)

        // When
        viewModel.updateStroke(point)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        verify { mockController.updateLatestPath(point) }
    }

    @Test
    fun testFinishStroke_finishesPath() = runBlocking {
        // Given
        viewModel.startStroke(Offset(10f, 20f), StrokeModifier.None)

        // When
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        verify { mockController.finishPath() }
        assertFalse(viewModel.isStrokeDown)
    }

    @Test
    fun testResolvePenType_withPrimaryButton_returnsStrokeEraser() {
        // When
        val result = viewModel.resolvePenType(StrokeModifier.PrimaryButton)

        // Then
        assertEquals(PenType.StrokeEraser, result)
    }

    @Test
    fun testResolvePenType_withNone_returnsCurrentPenType() = runBlocking {
        // When
        val result = viewModel.resolvePenType(StrokeModifier.None)

        // Then
        assertEquals(PenType.Pen, result)
    }

    @Test
    fun testAutoClearCanvas_clearsOnHide() = runBlocking {
        // Given
        viewModel.setAutoClearCanvas(true)
        testDispatcher.scheduler.advanceUntilIdle()

        // When
        viewModel.setCanvasVisibility(false)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        verify { mockController.clearPaths() }
        assertFalse(viewModel.uiState.value.canvasPassthrough)
    }
}
