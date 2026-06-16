/*
DrawAnywhere: An Android application that lets you draw on top of other apps.
Copyright (C) 2025 shezik

This program is free software: you can redistribute it and/or modify it under the
terms of the GNU Affero General Public License as published by the Free Software
Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along
with this program. If not, see <https://www.gnu.org/licenses/>.
 */

package com.shezik.drawanywhere

import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import io.mockk.every
import io.mockk.mockk
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

/**
 * 集成测试：StylusAwareDrawing 手势处理与 ViewModel 的集成
 * 
 * 测试重点：
 * 1. 手写笔按钮检测逻辑
 * 2. 笔刷类型自动切换
 * 3. 完整笔画生命周期（开始→更新→结束）
 * 4. 笔画结束后恢复之前的笔刷类型
 * 
 * 注意：由于无法在集成测试中注入真实的触摸事件，
 * 我们直接测试 ViewModel 的 startStroke/updateStroke/finishStroke 方法，
 * 这些方法是 stylusAwareDrawing Modifier 调用的核心接口。
 */
@OptIn(ExperimentalCoroutinesApi::class)
class StylusAwareDrawingIntegrationTest {

    private lateinit var viewModel: DrawViewModel
    private lateinit var controller: DrawController
    private lateinit var mockPreferencesMgr: PreferencesManager

    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        
        // 创建真实的 Controller
        controller = DrawController()
        controller.setPenConfig(PenConfig(penType = PenType.Pen, color = Color.Red, width = 5f, alpha = 1f))
        
        // Mock PreferencesManager
        mockPreferencesMgr = mockk(relaxed = true)
        every { runBlocking { mockPreferencesMgr.getSavedUiState() } } returns UiState()
        every { runBlocking { mockPreferencesMgr.getSavedServiceState() } } returns ServiceState()

        val initialUiState = UiState()
        val initialServiceState = ServiceState()

        viewModel = DrawViewModel(
            controller = controller,
            preferencesMgr = mockPreferencesMgr,
            initialUiState = initialUiState,
            initialServiceState = initialServiceState,
            stopService = { }
        )
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    /**
     * 测试用例 1: 普通触摸使用当前笔刷类型
     * 
     * 验证点：
     * - StrokeModifier.None 时，resolvePenType 返回当前笔刷类型
     * - 创建的路径使用 Pen 配置
     */
    @Test
    fun testNormalTouch_usesCurrentPenType() = runBlocking {
        // Given
        assertEquals(PenType.Pen, viewModel.uiState.value.currentPenType)
        val startPoint = Offset(10f, 20f)

        // When - 模拟普通触摸（无修饰符）
        viewModel.startStroke(startPoint, StrokeModifier.None)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证使用当前笔刷类型
        assertEquals(PenType.Pen, viewModel.uiState.value.currentPenType)
        assertEquals(1, controller.pathList.size)
        
        // 验证路径使用 Pen 的配置
        val path = controller.pathList[0]
        assertEquals(Color.Red, path.color)
        assertEquals(5f, path.width)
        
        viewModel.finishStroke()
    }

    /**
     * 测试用例 2: 主按钮切换到橡皮擦
     * 
     * 验证点：
     * - StrokeModifier.PrimaryButton 时，resolvePenType 返回 StrokeEraser
     * - 橡皮擦操作删除路径而非创建新路径
     */
    @Test
    fun testPrimaryButton_switchesToEraser() = runBlocking {
        // Given - 先创建一条路径
        viewModel.startStroke(Offset(10f, 10f), StrokeModifier.None)
        viewModel.updateStroke(Offset(20f, 20f))
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertEquals(1, controller.pathList.size)

        // When - 模拟按下主按钮的触摸（应触发橡皮擦）
        viewModel.startStroke(Offset(15f, 15f), StrokeModifier.PrimaryButton)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证切换到橡皮擦并删除路径
        assertEquals(PenType.StrokeEraser, viewModel.uiState.value.currentPenType)
        assertEquals(0, controller.pathList.size)
        
        viewModel.finishStroke()
    }

    /**
     * 测试用例 3: 副按钮也切换到橡皮擦
     * 
     * 验证点：
     * - StrokeModifier.SecondaryButton 同样触发橡皮擦
     */
    @Test
    fun testSecondaryButton_switchesToEraser() = runBlocking {
        // Given - 先创建一条路径
        viewModel.startStroke(Offset(10f, 10f), StrokeModifier.None)
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertEquals(1, controller.pathList.size)

        // When - 模拟按下副按钮
        viewModel.startStroke(Offset(15f, 15f), StrokeModifier.SecondaryButton)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证切换到橡皮擦
        assertEquals(PenType.StrokeEraser, viewModel.uiState.value.currentPenType)
        assertEquals(0, controller.pathList.size)
        
        viewModel.finishStroke()
    }

    /**
     * 测试用例 4: 同时按下两个按钮
     * 
     * 验证点：
     * - StrokeModifier.Both 也触发橡皮擦
     */
    @Test
    fun testBothButtons_switchesToEraser() = runBlocking {
        // Given - 先创建一条路径
        viewModel.startStroke(Offset(10f, 10f), StrokeModifier.None)
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertEquals(1, controller.pathList.size)

        // When - 模拟同时按下两个按钮
        viewModel.startStroke(Offset(15f, 15f), StrokeModifier.Both)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证切换到橡皮擦
        assertEquals(PenType.StrokeEraser, viewModel.uiState.value.currentPenType)
        assertEquals(0, controller.pathList.size)
        
        viewModel.finishStroke()
    }

    /**
     * 测试用例 5: 完整笔画生命周期
     * 
     * 验证点：
     * - startStroke 创建路径并设置 isStrokeDown
     * - updateStroke 添加点到路径
     * - finishStroke 完成路径并重置 isStrokeDown
     */
    @Test
    fun testCompleteStroke_lifecycle() = runBlocking {
        // Given
        val startPoint = Offset(10f, 20f)
        val midPoint = Offset(30f, 40f)
        val endPoint = Offset(50f, 60f)

        // When - 开始笔画
        viewModel.startStroke(startPoint, StrokeModifier.None)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证路径创建
        assertEquals(1, controller.pathList.size)
        assertEquals(1, controller.pathList[0].points.size)
        assertTrue(viewModel.isStrokeDown)

        // When - 更新笔画（移动）
        viewModel.updateStroke(midPoint)
        viewModel.updateStroke(endPoint)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证点被添加
        assertEquals(3, controller.pathList[0].points.size)
        assertEquals(startPoint, controller.pathList[0].points[0])
        assertEquals(midPoint, controller.pathList[0].points[1])
        assertEquals(endPoint, controller.pathList[0].points[2])

        // When - 结束笔画
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证状态重置
        assertFalse(viewModel.isStrokeDown)
        assertTrue(viewModel.canUndo.value)
    }

    /**
     * 测试用例 6: 笔画结束后恢复之前的笔刷类型
     * 
     * 验证点：
     * - 使用橡皮擦后，finishStroke 恢复为之前的 Pen 类型
     * - previousPenType 被正确保存和恢复
     */
    @Test
    fun testPenTypeRestoration_afterStroke() = runBlocking {
        // Given - 初始为 Pen
        assertEquals(PenType.Pen, viewModel.uiState.value.currentPenType)
        
        // 创建一条路径用于擦除
        viewModel.startStroke(Offset(10f, 10f), StrokeModifier.None)
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()

        // When - 使用橡皮擦（通过主按钮）
        viewModel.startStroke(Offset(15f, 15f), StrokeModifier.PrimaryButton)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证临时切换到橡皮擦
        assertEquals(PenType.StrokeEraser, viewModel.uiState.value.currentPenType)
        
        // When - 结束笔画
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证恢复为 Pen
        assertEquals(PenType.Pen, viewModel.uiState.value.currentPenType)
        assertNull(viewModel.previousPenType)
    }

    /**
     * 测试用例 7: 连续绘制多个笔画
     * 
     * 验证点：
     * - 多个笔画正确添加到 pathList
     * - 每个笔画有独立的点列表
     */
    @Test
    fun testMultipleStrokes_separatePaths() = runBlocking {
        // When - 绘制第一条笔画
        viewModel.startStroke(Offset(10f, 10f), StrokeModifier.None)
        viewModel.updateStroke(Offset(20f, 20f))
        viewModel.finishStroke()
        
        // 绘制第二条笔画
        viewModel.startStroke(Offset(30f, 30f), StrokeModifier.None)
        viewModel.updateStroke(Offset(40f, 40f))
        viewModel.updateStroke(Offset(50f, 50f))
        viewModel.finishStroke()
        
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证两条独立的路径
        assertEquals(2, controller.pathList.size)
        assertEquals(2, controller.pathList[0].points.size)
        assertEquals(3, controller.pathList[1].points.size)
    }

    /**
     * 测试用例 8: 未完成笔画的处理
     * 
     * 验证点：
     * - 开始新笔画时自动完成之前的笔画（不支持多点触控）
     */
    @Test
    fun testUnfinishedStroke_autoFinished() = runBlocking {
        // When - 开始第一个笔画但不结束
        viewModel.startStroke(Offset(10f, 10f), StrokeModifier.None)
        viewModel.updateStroke(Offset(20f, 20f))
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertEquals(1, controller.pathList.size)
        assertEquals(2, controller.pathList[0].points.size)

        // When - 开始第二个笔画（应自动结束第一个）
        viewModel.startStroke(Offset(30f, 30f), StrokeModifier.None)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证第一个笔画已被完成并添加到列表
        assertEquals(2, controller.pathList.size)
        // 第一个笔画应该有 2 个点
        assertEquals(2, controller.pathList[0].points.size)
        // 第二个笔画刚开始，有 1 个点
        assertEquals(1, controller.pathList[1].points.size)
        
        viewModel.finishStroke()
    }

    /**
     * 测试用例 9: 橡皮擦未命中路径时不删除
     * 
     * 验证点：
     * - 橡皮擦远离路径时不触发删除
     * - 笔刷类型仍然临时切换
     */
    @Test
    fun testEraserMiss_doesNotDelete() = runBlocking {
        // Given - 创建一条路径在 (100, 100) 附近
        viewModel.startStroke(Offset(100f, 100f), StrokeModifier.None)
        viewModel.updateStroke(Offset(110f, 110f))
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertEquals(1, controller.pathList.size)

        // When - 在远处使用橡皮擦（未命中）
        viewModel.startStroke(Offset(0f, 0f), StrokeModifier.PrimaryButton)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证路径未被删除
        assertEquals(1, controller.pathList.size)
        // 但笔刷类型仍切换为橡皮擦
        assertEquals(PenType.StrokeEraser, viewModel.uiState.value.currentPenType)
        
        viewModel.finishStroke()
    }

    /**
     * 测试用例 10: resolvePenType 方法的完整逻辑
     * 
     * 验证点：
     * - 所有 StrokeModifier 枚举值都能正确解析
     */
    @Test
    fun testResolvePenType_allModifiers() = runBlocking {
        // Given
        viewModel.switchToPen(PenType.Pen)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证各种修饰符的解析结果
        assertEquals(PenType.StrokeEraser, viewModel.resolvePenType(StrokeModifier.PrimaryButton))
        assertEquals(PenType.StrokeEraser, viewModel.resolvePenType(StrokeModifier.SecondaryButton))
        assertEquals(PenType.StrokeEraser, viewModel.resolvePenType(StrokeModifier.Both))
        assertEquals(PenType.Pen, viewModel.resolvePenType(StrokeModifier.None))
        
        // 切换到橡皮擦后再测试
        viewModel.switchToPen(PenType.StrokeEraser)
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertEquals(PenType.StrokeEraser, viewModel.resolvePenType(StrokeModifier.None))
    }
}
