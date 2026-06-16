package com.shezik.drawanywhere

import androidx.compose.ui.geometry.Offset
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import kotlin.math.sqrt

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class DrawUtilsTest {

    @Test
    fun testDistanceSquared_samePoint_returnsZero() {
        val point = Offset(5f, 10f)
        val result = distanceSquared(point, point)
        assertEquals(0f, result, 0.001f)
    }

    @Test
    fun testDistanceSquared_differentPoints_calculatesCorrectly() {
        val p1 = Offset(0f, 0f)
        val p2 = Offset(3f, 4f)
        val result = distanceSquared(p1, p2)
        assertEquals(25f, result, 0.001f)  // 3^2 + 4^2 = 9 + 16 = 25
    }

    @Test
    fun testDistance_samePoint_returnsZero() {
        val point = Offset(5f, 10f)
        val result = distance(point, point)
        assertEquals(0f, result, 0.001f)
    }

    @Test
    fun testDistance_differentPoints_calculatesCorrectly() {
        val p1 = Offset(0f, 0f)
        val p2 = Offset(3f, 4f)
        val result = distance(p1, p2)
        assertEquals(5f, result, 0.001f)  // sqrt(3^2 + 4^2) = 5
    }

    @Test
    fun testDistancePointToLineSegment_pointOnLine_returnsZero() {
        val a = Offset(0f, 0f)
        val b = Offset(10f, 0f)
        val p = Offset(5f, 0f)
        val result = distancePointToLineSegment(p, a, b)
        assertEquals(0f, result, 0.001f)
    }

    @Test
    fun testDistancePointToLineSegment_pointAboveLine_calculatesCorrectly() {
        val a = Offset(0f, 0f)
        val b = Offset(10f, 0f)
        val p = Offset(5f, 5f)
        val result = distancePointToLineSegment(p, a, b)
        assertEquals(5f, result, 0.001f)
    }

    @Test
    fun testDistancePointToLineSegment_pointBeforeStart_usesStartPoint() {
        val a = Offset(0f, 0f)
        val b = Offset(10f, 0f)
        val p = Offset(-5f, 0f)
        val result = distancePointToLineSegment(p, a, b)
        assertEquals(5f, result, 0.001f)
    }

    @Test
    fun testDistancePointToLineSegment_pointAfterEnd_usesEndPoint() {
        val a = Offset(0f, 0f)
        val b = Offset(10f, 0f)
        val p = Offset(15f, 0f)
        val result = distancePointToLineSegment(p, a, b)
        assertEquals(5f, result, 0.001f)
    }

    @Test
    fun testDistancePointToLineSegment_sameStartAndEnd_usesPointDistance() {
        val a = Offset(5f, 5f)
        val b = Offset(5f, 5f)
        val p = Offset(8f, 9f)
        val result = distancePointToLineSegment(p, a, b)
        val expected = distance(p, a)
        assertEquals(expected, result, 0.001f)
    }

    @Test
    fun testCalculateMidpoint_calculatesCorrectly() {
        val start = Offset(0f, 0f)
        val end = Offset(10f, 20f)
        val midpoint = calculateMidpoint(start, end)
        assertEquals(5f, midpoint.x, 0.001f)
        assertEquals(10f, midpoint.y, 0.001f)
    }

    @Test
    fun testCalculateMidpoint_samePoints_returnsSamePoint() {
        val point = Offset(5f, 10f)
        val midpoint = calculateMidpoint(point, point)
        assertEquals(point.x, midpoint.x, 0.001f)
        assertEquals(point.y, midpoint.y, 0.001f)
    }

    @Test
    fun testPointsToPath_emptyList_returnsEmptyPath() {
        val points = emptyList<Offset>()
        val path = pointsToPath(points)
        assertTrue(path.isEmpty)
    }

    @Test
    fun testPointsToPath_singlePoint_createsPathWithMoveTo() {
        val points = listOf(Offset(10f, 20f))
        val path = pointsToPath(points)
        assertFalse(path.isEmpty)
    }

    @Test
    fun testPointsToPath_multiplePoints_createsSmoothPath() {
        val points = listOf(
            Offset(0f, 0f),
            Offset(10f, 10f),
            Offset(20f, 20f)
        )
        val path = pointsToPath(points)
        assertFalse(path.isEmpty)
    }

    @Test
    fun testPointsToPath_twoPoints_createsLine() {
        val points = listOf(
            Offset(0f, 0f),
            Offset(10f, 10f)
        )
        val path = pointsToPath(points)
        assertFalse(path.isEmpty)
    }
}
