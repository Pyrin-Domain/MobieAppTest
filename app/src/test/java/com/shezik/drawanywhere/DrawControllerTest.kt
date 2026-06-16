package com.shezik.drawanywhere

import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class DrawControllerTest {

    private lateinit var controller: DrawController

    @Before
    fun setup() {
        controller = DrawController()
        controller.setPenConfig(PenConfig(penType = PenType.Pen, color = Color.Red, width = 5f, alpha = 1f))
    }

    @Test
    fun testCreatePath_addsPathToList() {
        // Given
        val point = Offset(10f, 20f)

        // When
        controller.createPath(point)

        // Then
        assertEquals(1, controller.pathList.size)
        assertEquals(1, controller.pathList[0].points.size)
        assertEquals(point, controller.pathList[0].points[0])
    }

    @Test
    fun testUpdateLatestPath_addsPointToExistingPath() {
        // Given
        val point1 = Offset(10f, 20f)
        val point2 = Offset(30f, 40f)
        controller.createPath(point1)

        // When
        controller.updateLatestPath(point2)

        // Then
        assertEquals(1, controller.pathList.size)
        assertEquals(2, controller.pathList[0].points.size)
        assertEquals(point1, controller.pathList[0].points[0])
        assertEquals(point2, controller.pathList[0].points[1])
    }

    @Test
    fun testFinishPath_addsToUndoStack() = runBlocking {
        // Given
        val point = Offset(10f, 20f)
        controller.createPath(point)

        // When
        controller.finishPath()

        // Then
        assertTrue(controller.canUndo.first())
        assertFalse(controller.canRedo.first())
    }

    @Test
    fun testUndo_removesLastPath() = runBlocking {
        // Given
        val point = Offset(10f, 20f)
        controller.createPath(point)
        controller.finishPath()

        // When
        controller.undo()

        // Then
        assertEquals(0, controller.pathList.size)
        assertFalse(controller.canUndo.first())
        assertTrue(controller.canRedo.first())
    }

    @Test
    fun testRedo_restoresUndonePath() = runBlocking {
        // Given
        val point = Offset(10f, 20f)
        controller.createPath(point)
        controller.finishPath()
        controller.undo()

        // When
        controller.redo()

        // Then
        assertEquals(1, controller.pathList.size)
        assertTrue(controller.canUndo.first())
        assertFalse(controller.canRedo.first())
    }

    @Test
    fun testClearPaths_removesAllPaths() = runBlocking {
        // Given
        controller.createPath(Offset(10f, 20f))
        controller.finishPath()
        controller.createPath(Offset(30f, 40f))
        controller.finishPath()

        // When
        controller.clearPaths()

        // Then
        assertEquals(0, controller.pathList.size)
        assertTrue(controller.canUndo.first())
        assertFalse(controller.canClearPaths.first())
    }

    @Test
    fun testStrokeEraser_removesPathOnTouch() = runBlocking {
        // Given
        controller.setPenConfig(PenConfig(penType = PenType.Pen, color = Color.Red, width = 5f))
        controller.createPath(Offset(10f, 10f))
        controller.updateLatestPath(Offset(20f, 20f))
        controller.finishPath()

        // When - switch to eraser and touch the path
        controller.setPenConfig(PenConfig(penType = PenType.StrokeEraser, width = 50f))
        controller.createPath(Offset(15f, 15f))  // Touch near the path

        // Then
        assertEquals(0, controller.pathList.size)
        assertTrue(controller.canUndo.first())
    }

    @Test
    fun testMultipleUndoOperations() = runBlocking {
        // Given
        controller.createPath(Offset(10f, 20f))
        controller.finishPath()
        controller.createPath(Offset(30f, 40f))
        controller.finishPath()
        controller.createPath(Offset(50f, 60f))
        controller.finishPath()

        // When
        controller.undo()
        controller.undo()

        // Then
        assertEquals(1, controller.pathList.size)
        assertTrue(controller.canUndo.first())
        assertTrue(controller.canRedo.first())
    }

    @Test
    fun testUndoDepthLimit() = runBlocking {
        // Given - create more paths than maxUndoDepth (50)
        for (i in 1..55) {
            controller.createPath(Offset(i.toFloat(), i.toFloat()))
            controller.finishPath()
        }

        // When
        val initialSize = controller.pathList.size

        // Then - should still have all paths
        assertEquals(55, initialSize)
        
        // Undo 50 times (maxUndoDepth)
        for (i in 1..50) {
            assertTrue("Should be able to undo iteration $i", controller.canUndo.value)
            controller.undo()
        }
        
        // After 50 undos, we've removed 50 paths, leaving 5
        assertEquals(5, controller.pathList.size)
        // Undo stack should now be empty (we hit the limit)
        assertEquals(false, controller.canUndo.value)
    }

    @Test
    fun testNewActionClearsRedoStack() = runBlocking {
        // Given
        controller.createPath(Offset(10f, 20f))
        controller.finishPath()
        controller.undo()
        assertTrue(controller.canRedo.first())

        // When - create a new path
        controller.createPath(Offset(30f, 40f))
        controller.finishPath()

        // Then - redo stack should be cleared
        assertFalse(controller.canRedo.first())
    }

    @Test(expected = IllegalStateException::class)
    fun testCreatePathWithoutPenConfig_throwsException() {
        // Given
        val newController = DrawController()

        // When
        newController.createPath(Offset(10f, 20f))

        // Then - should throw IllegalStateException
    }

    @Test
    fun testEmptyPathNotAddedOnFinish() = runBlocking {
        // Given - create a path but don't add any points
        // This scenario shouldn't normally happen, but testing edge case

        // When
        controller.finishPath()

        // Then
        assertEquals(0, controller.pathList.size)
    }

    @Test
    fun testCanClearPathsState() = runBlocking {
        // Given
        assertEquals(false, controller.canClearPaths.value)

        // When
        controller.createPath(Offset(10f, 20f))
        controller.finishPath()  // Need to finish path to update canClearPaths state

        // Then
        assertEquals(true, controller.canClearPaths.value)

        // When
        controller.clearPaths()

        // Then
        assertEquals(false, controller.canClearPaths.value)
    }
}
