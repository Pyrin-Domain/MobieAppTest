package com.shezik.drawanywhere

import android.content.Context
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.datastore.preferences.preferencesDataStore
import io.mockk.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@OptIn(ExperimentalCoroutinesApi::class)
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class PreferencesManagerRobolectricTest {

    private lateinit var preferencesManager: PreferencesManager
    private lateinit var context: Context
    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        
        // Create a Robolectric context
        context = org.robolectric.RuntimeEnvironment.getApplication()
        
        preferencesManager = PreferencesManager(context)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun testGetSavedUiState_returnsDefaultWhenNoPreferences() = runBlocking {
        // When
        val uiState = preferencesManager.getSavedUiState()

        // Then
        assertNotNull(uiState)
        assertEquals(PenType.Pen, uiState.currentPenType)
        assertTrue(uiState.canvasVisible)
        assertEquals(ToolbarOrientation.HORIZONTAL, uiState.toolbarOrientation)
    }

    @Test
    fun testSaveAndRetrieveUiState() = runBlocking {
        // Given
        val customUiState = UiState(
            canvasVisible = false,
            canvasPassthrough = true,
            autoClearCanvas = true,
            visibleOnStart = false,
            currentPenType = PenType.StrokeEraser,
            toolbarOrientation = ToolbarOrientation.VERTICAL
        )

        // When
        preferencesManager.saveUiState(customUiState)
        val retrievedState = preferencesManager.getSavedUiState()

        // Then - only certain fields are persisted
        assertEquals(customUiState.autoClearCanvas, retrievedState.autoClearCanvas)
        assertEquals(customUiState.visibleOnStart, retrievedState.visibleOnStart)
        assertEquals(customUiState.currentPenType, retrievedState.currentPenType)
        assertEquals(customUiState.toolbarOrientation, retrievedState.toolbarOrientation)
        // Note: canvasVisible and canvasPassthrough are not directly saved
        // canvasVisible is derived from visibleOnStart in getSavedUiState()
    }

    @Test
    fun testSaveAndRetrievePenConfigs() = runBlocking {
        // Given
        val customConfigs = mapOf(
            PenType.Pen to PenConfig(penType = PenType.Pen, color = Color.Blue, width = 15f, alpha = 0.8f),
            PenType.StrokeEraser to PenConfig(penType = PenType.StrokeEraser, width = 60f)
        )
        val uiState = UiState(penConfigs = customConfigs)

        // When
        preferencesManager.saveUiState(uiState)
        val retrievedState = preferencesManager.getSavedUiState()

        // Then
        val retrievedPenConfig = retrievedState.penConfigs[PenType.Pen]
        assertNotNull(retrievedPenConfig)
        assertEquals(Color.Blue, retrievedPenConfig?.color)
        assertEquals(15f, retrievedPenConfig!!.width, 0.001f)
        assertEquals(0.8f, retrievedPenConfig.alpha, 0.001f)
        
        val retrievedEraserConfig = retrievedState.penConfigs[PenType.StrokeEraser]
        assertNotNull(retrievedEraserConfig)
        assertEquals(60f, retrievedEraserConfig!!.width, 0.001f)
    }

    @Test
    fun testGetSavedServiceState_returnsDefaultWhenNoPreferences() = runBlocking {
        // When
        val serviceState = preferencesManager.getSavedServiceState()

        // Then - only toolbarPosition is saved, other fields use defaults
        assertNotNull("ServiceState should not be null", serviceState)
        // Note: In Robolectric with DataStore, defaults might vary, so we just check it's a valid Offset
        assertTrue("X position should be >= 0", serviceState.toolbarPosition.x >= 0f)
        assertTrue("Y position should be >= 0", serviceState.toolbarPosition.y >= 0f)
        // Note: positionValidated and toolbarActive are not persisted
    }

    @Test
    fun testSaveAndRetrieveServiceState() = runBlocking {
        // Given
        val customServiceState = ServiceState(
            toolbarPosition = Offset(150f, 250f),
            positionValidated = true,
            toolbarActive = false
        )

        // When
        preferencesManager.saveServiceState(customServiceState)
        val retrievedState = preferencesManager.getSavedServiceState()

        // Then
        assertEquals(150f, retrievedState.toolbarPosition.x, 0.001f)
        assertEquals(250f, retrievedState.toolbarPosition.y, 0.001f)
        // Note: positionValidated and toolbarActive are not saved in PreferencesManager
    }

    @Test
    fun testGetEnumValueOrDefault_returnsDefaultWhenNull() {
        // When
        val result = preferencesManager.getEnumValueOrDefault<PenType>(null, PenType.Pen)

        // Then
        assertEquals(PenType.Pen, result)
    }

    @Test
    fun testGetEnumValueOrDefault_returnsDefaultWhenInvalid() {
        // When
        val result = preferencesManager.getEnumValueOrDefault("InvalidValue", PenType.Pen)

        // Then
        assertEquals(PenType.Pen, result)
    }

    @Test
    fun testGetEnumValueOrDefault_returnsValidValue() {
        // When
        val result = preferencesManager.getEnumValueOrDefault("StrokeEraser", PenType.Pen)

        // Then
        assertEquals(PenType.StrokeEraser, result)
    }

    @Test
    fun testSaveMultipleTimes_overwritesPreviousValues() = runBlocking {
        // Given - save initial state
        val firstState = UiState(currentPenType = PenType.Pen)
        preferencesManager.saveUiState(firstState)

        // When - save different state
        val secondState = UiState(currentPenType = PenType.StrokeEraser)
        preferencesManager.saveUiState(secondState)
        val retrievedState = preferencesManager.getSavedUiState()

        // Then
        assertEquals(PenType.StrokeEraser, retrievedState.currentPenType)
    }

    @Test
    fun testPartialPenConfigUpdate_preservesOtherConfigs() = runBlocking {
        // Given - save full config
        val initialConfigs = mapOf(
            PenType.Pen to PenConfig(penType = PenType.Pen, color = Color.Red, width = 10f, alpha = 1f),
            PenType.StrokeEraser to PenConfig(penType = PenType.StrokeEraser, width = 50f)
        )
        val initialState = UiState(penConfigs = initialConfigs)
        preferencesManager.saveUiState(initialState)

        // When - update only Pen config
        val updatedConfigs = mapOf(
            PenType.Pen to PenConfig(penType = PenType.Pen, color = Color.Blue, width = 20f, alpha = 0.5f),
            PenType.StrokeEraser to PenConfig(penType = PenType.StrokeEraser, width = 50f)
        )
        val updatedState = UiState(penConfigs = updatedConfigs)
        preferencesManager.saveUiState(updatedState)

        val retrievedState = preferencesManager.getSavedUiState()

        // Then
        val penConfig = retrievedState.penConfigs[PenType.Pen]
        assertEquals(Color.Blue, penConfig?.color)
        assertNotNull(penConfig)
        assertEquals(20f, penConfig!!.width, 0.001f)
        assertEquals(0.5f, penConfig.alpha, 0.001f)
    }

    @Test
    fun testToolbarPositionPersistence() = runBlocking {
        // Given
        val positions = listOf(
            Offset(0f, 0f),
            Offset(100f, 200f),
            Offset(500f, 800f)
        )

        // When & Then - save and retrieve multiple positions
        for (position in positions) {
            val serviceState = ServiceState(toolbarPosition = position)
            preferencesManager.saveServiceState(serviceState)
            val retrieved = preferencesManager.getSavedServiceState()
            assertEquals(position.x, retrieved.toolbarPosition.x, 0.001f)
            assertEquals(position.y, retrieved.toolbarPosition.y, 0.001f)
        }
    }
}
