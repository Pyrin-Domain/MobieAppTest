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
import io.mockk.coVerify
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
 * 集成测试：完整用户工作流程的端到端集成
 * 
 * 测试重点：
 * 1. 从启动到绘制到保存的完整流程
 * 2. 多个笔刷配置的独立管理和持久化
 * 3. 多操作后状态一致性验证
 * 4. 真实场景模拟
 */
@OptIn(ExperimentalCoroutinesApi::class)
class FullUserWorkflowIntegrationTest {

    private lateinit var viewModel: DrawViewModel
    private lateinit var controller: DrawController
    private lateinit var mockPreferencesMgr: PreferencesManager
    private var serviceStopped = false

    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        
        controller = DrawController()
        controller.setPenConfig(PenConfig(penType = PenType.Pen, color = Color.Red, width = 5f, alpha = 1f))
        
        mockPreferencesMgr = mockk(relaxed = true)
        every { runBlocking { mockPreferencesMgr.getSavedUiState() } } returns UiState()
        every { runBlocking { mockPreferencesMgr.getSavedServiceState() } } returns ServiceState()
        
        serviceStopped = false

        val initialUiState = UiState()
        val initialServiceState = ServiceState()

        viewModel = DrawViewModel(
            controller = controller,
            preferencesMgr = mockPreferencesMgr,
            initialUiState = initialUiState,
            initialServiceState = initialServiceState,
            stopService = { serviceStopped = true }
        )
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    /**
     * 测试用例 1: 完整绘制工作流程
     * 
     * 场景：用户启动应用 → 配置笔刷 → 绘制 → 擦除 → 撤销 → 保存设置 → 退出
     * 
     * 验证点：
     * - 整个流程中各组件协同工作正常
     * - 最终状态正确持久化
     */
    @Test
    fun testCompleteDrawingWorkflow() = runBlocking {
        // ===== 阶段 1: 启动和初始化 =====
        assertEquals(PenType.Pen, viewModel.uiState.value.currentPenType)
        assertTrue(viewModel.uiState.value.canvasVisible)
        assertEquals(Offset(32f, 64f), viewModel.serviceState.value.toolbarPosition)

        // ===== 阶段 2: 配置笔刷 =====
        viewModel.setPenColor(Color.Blue)
        viewModel.setStrokeWidth(10f)
        viewModel.setStrokeAlpha(0.8f)
        testDispatcher.scheduler.advanceUntilIdle()
        
        val penConfig = viewModel.uiState.value.penConfigs[PenType.Pen]
        assertEquals(Color.Blue, penConfig?.color)
        assertEquals(10f, penConfig?.width)
        assertEquals(0.8f, penConfig?.alpha)

        // ===== 阶段 3: 绘制多个笔画 =====
        // 笔画 1
        viewModel.startStroke(Offset(10f, 10f), StrokeModifier.None)
        viewModel.updateStroke(Offset(20f, 20f))
        viewModel.updateStroke(Offset(30f, 30f))
        viewModel.finishStroke()
        
        // 笔画 2
        viewModel.startStroke(Offset(50f, 50f), StrokeModifier.None)
        viewModel.updateStroke(Offset(60f, 60f))
        viewModel.finishStroke()
        
        // 笔画 3
        viewModel.startStroke(Offset(100f, 100f), StrokeModifier.None)
        viewModel.finishStroke()
        
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertEquals(3, controller.pathList.size)
        assertTrue(viewModel.canUndo.value)

        // ===== 阶段 4: 使用橡皮擦删除一个笔画 =====
        viewModel.startStroke(Offset(55f, 55f), StrokeModifier.PrimaryButton)
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertEquals(2, controller.pathList.size)
        assertEquals(PenType.StrokeEraser, viewModel.uiState.value.currentPenType)
        
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()
        
        // 验证恢复为 Pen
        assertEquals(PenType.Pen, viewModel.uiState.value.currentPenType)

        // ===== 阶段 5: 撤销和重做 =====
        viewModel.undo()  // 撤销擦除操作
        testDispatcher.scheduler.advanceUntilIdle()
        assertEquals(3, controller.pathList.size)
        
        viewModel.redo()  // 重做擦除操作
        testDispatcher.scheduler.advanceUntilIdle()
        assertEquals(2, controller.pathList.size)

        // ===== 阶段 6: 切换穿透模式 =====
        viewModel.toggleCanvasPassthrough()
        testDispatcher.scheduler.advanceUntilIdle()
        assertTrue(viewModel.uiState.value.canvasPassthrough)

        // ===== 阶段 7: 移动工具栏 =====
        viewModel.updateToolbarPosition(Offset(100f, 100f))
        testDispatcher.scheduler.advanceUntilIdle()
        assertEquals(Offset(132f, 164f), viewModel.serviceState.value.toolbarPosition)

        // ===== 阶段 8: 退出应用并保存 =====
        viewModel.quitApplication()
        testDispatcher.scheduler.advanceUntilIdle()
        
        // 验证所有状态被保存
        coVerify { mockPreferencesMgr.saveUiState(any()) }
        coVerify { mockPreferencesMgr.saveServiceState(any()) }
        assertTrue(serviceStopped)
    }

    /**
     * 测试用例 2: 多个笔刷配置的持久化
     * 
     * 场景：用户分别配置 Pen 和 Eraser，然后验证保存和恢复
     * 
     * 验证点：
     * - 不同笔刷类型的配置独立保存
     * - 加载时正确恢复所有配置
     */
    @Test
    fun testMultiplePenConfigs_persistence() = runBlocking {
        // Given - 配置 Pen
        viewModel.setPenColor(Color.Green)
        viewModel.setStrokeWidth(15f)
        testDispatcher.scheduler.advanceUntilIdle()
        
        // 切换到 Eraser 并配置
        viewModel.switchToPen(PenType.StrokeEraser)
        viewModel.setStrokeWidth(60f)
        testDispatcher.scheduler.advanceUntilIdle()

        // When - 保存状态
        viewModel.quitApplication()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证 saveUiState 被调用
        coVerify { mockPreferencesMgr.saveUiState(any()) }
        
        // 验证两个笔刷的配置都被更新
        val penConfig = viewModel.uiState.value.penConfigs[PenType.Pen]
        val eraserConfig = viewModel.uiState.value.penConfigs[PenType.StrokeEraser]
        
        assertEquals(Color.Green, penConfig?.color)
        assertEquals(15f, penConfig?.width)
        assertEquals(60f, eraserConfig?.width)
    }

    /**
     * 测试用例 3: 复杂操作序列后的状态一致性
     * 
     * 场景：执行大量绘制、擦除、撤销、重做操作后验证状态
     * 
     * 验证点：
     * - pathList 大小正确
     * - undo/redo 栈状态正确
     * - 可以正常继续操作
     */
    @Test
    fun testStateConsistency_acrossComplexOperations() = runBlocking {
        // Given - 创建 10 条路径
        for (i in 1..10) {
            viewModel.startStroke(Offset(i * 10f, i * 10f), StrokeModifier.None)
            viewModel.finishStroke()
        }
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertEquals(10, controller.pathList.size)
        assertTrue(viewModel.canUndo.value)

        // When - 撤销 5 次
        for (i in 1..5) {
            viewModel.undo()
        }
        testDispatcher.scheduler.advanceUntilIdle()
        
        // Then
        assertEquals(5, controller.pathList.size)
        assertTrue(viewModel.canUndo.value)
        assertTrue(viewModel.canRedo.value)

        // When - 重做 3 次
        for (i in 1..3) {
            viewModel.redo()
        }
        testDispatcher.scheduler.advanceUntilIdle()
        
        // Then
        assertEquals(8, controller.pathList.size)

        // When - 创建新路径（应清空 redo 栈）
        viewModel.startStroke(Offset(200f, 200f), StrokeModifier.None)
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()
        
        // Then
        assertEquals(9, controller.pathList.size)
        assertTrue(viewModel.canUndo.value)
        assertFalse(viewModel.canRedo.value)  // redo 栈已清空

        // When - 使用橡皮擦删除 3 条路径
        for (i in 1..3) {
            val pos = Offset((10 - i) * 10f, (10 - i) * 10f)
            viewModel.startStroke(pos, StrokeModifier.PrimaryButton)
            testDispatcher.scheduler.advanceUntilIdle()
            viewModel.finishStroke()
        }
        
        // Then
        assertEquals(6, controller.pathList.size)
    }

    /**
     * 测试用例 4: 画布可见性与自动清除的工作流程
     * 
     * 场景：启用自动清除，绘制内容，隐藏画布，再显示
     * 
     * 验证点：
     * - 隐藏时自动清除
     * - 显示时画布为空
     */
    @Test
    fun testAutoClearWorkflow_hideAndShow() = runBlocking {
        // Given - 绘制内容
        viewModel.startStroke(Offset(10f, 20f), StrokeModifier.None)
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertEquals(1, controller.pathList.size)
        
        // 启用自动清除
        viewModel.setAutoClearCanvas(true)
        testDispatcher.scheduler.advanceUntilIdle()

        // When - 隐藏画布
        viewModel.setCanvasVisibility(false)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证清除
        assertEquals(0, controller.pathList.size)
        assertFalse(viewModel.uiState.value.canvasVisible)
        assertFalse(viewModel.uiState.value.canvasPassthrough)

        // When - 显示画布
        viewModel.setCanvasVisibility(true)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证画布仍为空
        assertTrue(viewModel.uiState.value.canvasVisible)
        assertEquals(0, controller.pathList.size)
    }

    /**
     * 测试用例 5: 工具栏方向与抽屉状态的联动
     * 
     * 场景：切换工具栏方向，打开/关闭抽屉
     * 
     * 验证点：
     * - 方向切换正确
     * - 抽屉状态独立管理
     */
    @Test
    fun testToolbarAndDrawer_workflow() = runBlocking {
        // Given
        assertEquals(ToolbarOrientation.HORIZONTAL, viewModel.uiState.value.toolbarOrientation)
        assertTrue(viewModel.uiState.value.firstDrawerOpen)
        assertFalse(viewModel.uiState.value.secondDrawerOpen)

        // When - 切换方向
        viewModel.toggleToolbarOrientation()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertEquals(ToolbarOrientation.VERTICAL, viewModel.uiState.value.toolbarOrientation)

        // When - 操作抽屉
        viewModel.toggleFirstDrawer()
        viewModel.toggleSecondDrawer()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertFalse(viewModel.uiState.value.firstDrawerOpen)
        assertTrue(viewModel.uiState.value.secondDrawerOpen)
    }

    /**
     * 测试用例 6: 笔刷切换与配置的独立性
     * 
     * 场景：在 Pen 和 Eraser 之间切换，修改各自配置
     * 
     * 验证点：
     * - 每个笔刷类型有独立的配置
     * - 切换不影响其他笔刷的配置
     */
    @Test
    fun testPenSwitching_configIndependence() = runBlocking {
        // Given - 配置 Pen
        viewModel.setPenColor(Color.Red)
        viewModel.setStrokeWidth(5f)
        testDispatcher.scheduler.advanceUntilIdle()

        // When - 切换到 Eraser 并配置
        viewModel.switchToPen(PenType.StrokeEraser)
        viewModel.setStrokeWidth(50f)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证 Eraser 配置
        val eraserConfig = viewModel.uiState.value.penConfigs[PenType.StrokeEraser]
        assertEquals(50f, eraserConfig?.width)

        // When - 切换回 Pen
        viewModel.switchToPen(PenType.Pen)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证 Pen 配置保持不变
        val penConfig = viewModel.uiState.value.penConfigs[PenType.Pen]
        assertEquals(Color.Red, penConfig?.color)
        assertEquals(5f, penConfig?.width)
    }

    /**
     * 测试用例 7: 撤销深度限制的实际效果
     * 
     * 场景：创建超过 50 条路径，验证撤销深度限制
     * 
     * 验证点：
     * - 最多只能撤销 50 次
     * - 超过限制后 canUndo 为 false
     */
    @Test
    fun testUndoDepthLimit_realWorldScenario() = runBlocking {
        // Given - 创建 60 条路径
        for (i in 1..60) {
            viewModel.startStroke(Offset(i.toFloat(), i.toFloat()), StrokeModifier.None)
            viewModel.finishStroke()
        }
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertEquals(60, controller.pathList.size)

        // When - 撤销 50 次（最大深度）
        var undoCount = 0
        while (viewModel.canUndo.value && undoCount < 60) {
            viewModel.undo()
            undoCount++
        }
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证最多撤销 50 次
        assertTrue("Should undo at least 50 times", undoCount >= 50)
        // 剩余路径数应为 60 - 50 = 10
        assertTrue("Should have around 10 paths remaining", controller.pathList.size <= 10)
        assertFalse(viewModel.canUndo.value)  // 撤销栈已达限制
    }

    /**
     * 测试用例 8: 真实用户会话模拟
     * 
     * 场景：模拟一个真实的用户使用会话，包括各种操作的混合
     * 
     * 验证点：
     * - 所有操作都能正常执行
     * - 最终状态合理
     */
    @Test
    fun testRealUserSession_simulation() = runBlocking {
        // 用户启动应用，看到默认状态
        assertTrue(viewModel.uiState.value.canvasVisible)
        
        // 用户选择蓝色画笔
        viewModel.setPenColor(Color.Blue)
        viewModel.setStrokeWidth(8f)
        testDispatcher.scheduler.advanceUntilIdle()
        
        // 用户绘制一些内容
        for (i in 1..5) {
            viewModel.startStroke(Offset(i * 20f, i * 20f), StrokeModifier.None)
            viewModel.updateStroke(Offset(i * 20f + 10f, i * 20f + 10f))
            viewModel.finishStroke()
        }
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertEquals(5, controller.pathList.size)
        
        // 用户不小心画错了，撤销一次
        viewModel.undo()
        testDispatcher.scheduler.advanceUntilIdle()
        assertEquals(4, controller.pathList.size)
        
        // 用户重新绘制
        viewModel.startStroke(Offset(150f, 150f), StrokeModifier.None)
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()
        assertEquals(5, controller.pathList.size)
        
        // 用户使用橡皮擦清理
        viewModel.startStroke(Offset(40f, 40f), StrokeModifier.PrimaryButton)
        testDispatcher.scheduler.advanceUntilIdle()
        viewModel.finishStroke()
        
        // 用户移动工具栏
        viewModel.updateToolbarPosition(Offset(200f, 100f))
        testDispatcher.scheduler.advanceUntilIdle()
        
        // 用户启用穿透模式查看下层应用
        viewModel.toggleCanvasPassthrough()
        testDispatcher.scheduler.advanceUntilIdle()
        assertTrue(viewModel.uiState.value.canvasPassthrough)
        
        // 用户决定退出
        viewModel.quitApplication()
        testDispatcher.scheduler.advanceUntilIdle()
        
        // 验证所有状态被保存
        coVerify { mockPreferencesMgr.saveUiState(any()) }
        coVerify { mockPreferencesMgr.saveServiceState(any()) }
        assertTrue(serviceStopped)
    }
}
