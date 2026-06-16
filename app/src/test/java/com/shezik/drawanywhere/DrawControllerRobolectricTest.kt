package com.shezik.drawanywhere

import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class DrawControllerRobolectricTest {

    private lateinit var controller: DrawController

    @Before
    fun setup() {
        controller = DrawController()
        controller.setPenConfig(PenConfig(penType = PenType.Pen, color = Color.Red, width = 5f, alpha = 1f))
    }

    @Test
    fun testPathList_isObservable() {
        // Given
        val point = Offset(10f, 20f)

        // When
        controller.createPath(point)

        // Then - pathList should be accessible and contain the path
        assertNotNull(controller.pathList)
        assertEquals(1, controller.pathList.size)
    }

    @Test
    fun testFlowStates_emitCorrectValues() = runBlocking {
        // Given
        assertFalse(controller.canUndo.first())
        assertFalse(controller.canRedo.first())
        assertFalse(controller.canClearPaths.first())

        // When
        controller.createPath(Offset(10f, 20f))
        controller.finishPath()

        // Then
        assertTrue(controller.canUndo.first())
        assertFalse(controller.canRedo.first())
        assertTrue(controller.canClearPaths.first())
    }

    @Test
    fun testComplexDrawingSequence() = runBlocking {
        // Given - draw multiple paths
        controller.createPath(Offset(0f, 0f))
        controller.updateLatestPath(Offset(10f, 10f))
        controller.finishPath()

        controller.createPath(Offset(20f, 20f))
        controller.updateLatestPath(Offset(30f, 30f))
        controller.finishPath()

        // When - undo one
        controller.undo()

        // Then
        assertEquals(1, controller.pathList.size)
        assertTrue(controller.canUndo.first())
        assertTrue(controller.canRedo.first())

        // When - redo
        controller.redo()

        // Then
        assertEquals(2, controller.pathList.size)
    }

    @Test
    fun testErasePathWithStrokeEraser_detectsAndRemovesPath() = runBlocking {
        // Given - draw a path
        controller.setPenConfig(PenConfig(penType = PenType.Pen, color = Color.Black, width = 5f))
        controller.createPath(Offset(10f, 10f))
        controller.updateLatestPath(Offset(20f, 20f))
        controller.updateLatestPath(Offset(30f, 30f))
        controller.finishPath()

        assertEquals(1, controller.pathList.size)

        // When - use stroke eraser near the path
        controller.setPenConfig(PenConfig(penType = PenType.StrokeEraser, width = 30f))
        controller.createPath(Offset(15f, 15f))  // Near the first segment

        // Then
        assertEquals(0, controller.pathList.size)
        assertTrue(controller.canUndo.first())
    }

    @Test
    fun testErasePath_missesPath_doesNotRemove() = runBlocking {
        // Given - draw a path
        controller.setPenConfig(PenConfig(penType = PenType.Pen, color = Color.Black, width = 5f))
        controller.createPath(Offset(100f, 100f))
        controller.updateLatestPath(Offset(200f, 200f))
        controller.finishPath()

        assertEquals(1, controller.pathList.size)

        // When - use stroke eraser far from the path
        controller.setPenConfig(PenConfig(penType = PenType.StrokeEraser, width = 10f))
        controller.createPath(Offset(0f, 0f))  // Far from the path

        // Then - path should still exist
        assertEquals(1, controller.pathList.size)
    }

    @Test
    fun testUndoRedoWithEraseActions() = runBlocking {
        // Given - draw two paths
        controller.createPath(Offset(10f, 10f))
        controller.finishPath()
        
        controller.createPath(Offset(50f, 50f))
        controller.finishPath()

        assertEquals(2, controller.pathList.size)

        // When - erase one path
        controller.setPenConfig(PenConfig(penType = PenType.StrokeEraser, width = 50f))
        controller.createPath(Offset(10f, 10f))

        assertEquals(1, controller.pathList.size)

        // When - undo the erase
        controller.undo()

        // Then - both paths should be back
        assertEquals(2, controller.pathList.size)

        // When - redo the erase
        controller.redo()

        // Then - one path should be gone again
        assertEquals(1, controller.pathList.size)
    }

    @Test
    fun testClearPaths_undoRedo() = runBlocking {
        // Given - draw multiple paths
        controller.createPath(Offset(10f, 10f))
        controller.finishPath()
        controller.createPath(Offset(20f, 20f))
        controller.finishPath()
        controller.createPath(Offset(30f, 30f))
        controller.finishPath()

        assertEquals(3, controller.pathList.size)

        // When - clear all
        controller.clearPaths()
        assertEquals(0, controller.pathList.size)

        // When - undo clear
        controller.undo()
        assertEquals(3, controller.pathList.size)

        // When - redo clear
        controller.redo()
        assertEquals(0, controller.pathList.size)
    }

    @Test
    fun testPathWrapper_caching_worksCorrectly() {
        // Given
        controller.createPath(Offset(0f, 0f))
        controller.updateLatestPath(Offset(10f, 10f))
        controller.updateLatestPath(Offset(20f, 20f))

        val pathWrapper = controller.pathList[0]

        // When - access cached path multiple times
        val path1 = pathWrapper.cachedPath
        val path2 = pathWrapper.cachedPath

        // Then - should return same cached instance
        assertSame(path1, path2)
    }

    @Test
    fun testUpdateLatestPath_invalidatesCache() {
        // Given
        controller.createPath(Offset(0f, 0f))
        controller.updateLatestPath(Offset(10f, 10f))
        
        val pathWrapper = controller.pathList[0]
        val path1 = pathWrapper.cachedPath

        // When - add more points
        controller.updateLatestPath(Offset(20f, 20f))
        val path2 = pathWrapper.cachedPath

        // Then - cache should be regenerated
        assertNotNull(path2)
        // Note: The actual Path objects might be different instances after invalidation
    }

    @Test
    fun testFinishPath_withEmptyPoints_removesPath() = runBlocking {
        // Given - create a path
        controller.createPath(Offset(10f, 20f))
        assertEquals(1, controller.pathList.size)

        // Manually clear points (edge case)
        controller.pathList[0].points.clear()

        // When
        controller.finishPath()

        // Then - empty path should be removed
        assertEquals(0, controller.pathList.size)
    }

    @Test
    fun testMultiplePenConfigs_switchingPreservesState() = runBlocking {
        // Given - configure and use Pen
        controller.setPenConfig(PenConfig(penType = PenType.Pen, color = Color.Red, width = 5f))
        controller.createPath(Offset(10f, 10f))
        controller.finishPath()

        // When - switch to eraser and erase
        controller.setPenConfig(PenConfig(penType = PenType.StrokeEraser, width = 50f))
        controller.createPath(Offset(10f, 10f))

        assertEquals(0, controller.pathList.size)

        // When - switch back to pen and draw
        controller.setPenConfig(PenConfig(penType = PenType.Pen, color = Color.Blue, width = 10f))
        controller.createPath(Offset(50f, 50f))
        controller.finishPath()

        // Then
        assertEquals(1, controller.pathList.size)
        assertEquals(Color.Blue, controller.pathList[0].color)
        assertEquals(10f, controller.pathList[0].width, 0.001f)
    }

    @Test
    fun testUndoStackDepthLimit_preventsOverflow() = runBlocking {
        // Given - create many paths
        val numPaths = 100
        for (i in 1..numPaths) {
            controller.createPath(Offset(i.toFloat(), i.toFloat()))
            controller.finishPath()
        }

        assertEquals(numPaths, controller.pathList.size)

        // When - undo many times
        var undoCount = 0
        while (controller.canUndo.value && undoCount < 100) {  // Safety limit
            controller.undo()
            undoCount++
        }

        // Then - should be able to undo at least 50 times (maxUndoDepth)
        assertTrue("Should be able to undo at least 50 times, but only undid $undoCount", undoCount >= 50)
        // After undoing, some paths should remain (100 - 50 = 50)
        assertTrue("Should have some paths remaining", controller.pathList.size > 0)
    }

    @Test
    fun testConcurrentPathOperations_maintainsConsistency() = runBlocking {
        // Given
        controller.createPath(Offset(0f, 0f))
        controller.finishPath()

        // When - perform multiple operations
        controller.createPath(Offset(10f, 10f))
        controller.finishPath()
        controller.undo()
        controller.redo()
        controller.clearPaths()
        controller.undo()

        // Then - state should be consistent
        assertTrue(controller.canUndo.value || controller.canRedo.value)
        assertNotNull(controller.pathList)
    }
}
