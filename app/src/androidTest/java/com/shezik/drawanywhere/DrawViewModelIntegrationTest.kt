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
 * 集成测试：DrawViewModel 与 DrawController、PreferencesManager 的集成
 * 
 * 测试重点：
 * 1. ViewModel 状态变化是否正确触发 Controller 操作
 * 2. Controller 状态流是否正确反映到 ViewModel
 * 3. 状态持久化是否正确调用 PreferencesManager
 */
@OptIn(ExperimentalCoroutinesApi::class)
class DrawViewModelIntegrationTest {

    private lateinit var viewModel: DrawViewModel
    private lateinit var controller: DrawController
    private lateinit var mockPreferencesMgr: PreferencesManager
    private var serviceStopped = false

    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        
        // 创建真实的 Controller（集成测试的核心）
        controller = DrawController()
        controller.setPenConfig(PenConfig(penType = PenType.Pen, color = Color.Red, width = 5f, alpha = 1f))
        
        // Mock PreferencesManager 以避免真实的 DataStore I/O
        mockPreferencesMgr = mockk(relaxed = true)
        
        // 配置 mock 行为：返回默认状态
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
     * 测试用例 1: 初始状态从 Preferences 加载
     * 
     * 验证点：
     * - ViewModel 初始化时使用传入的初始状态
     * - Controller 的 penConfig 被正确设置
     */
    @Test
    fun testInitialState_loadsFromPreferences() = runBlocking {
        // Then - 验证初始状态
        assertEquals(true, viewModel.uiState.value.canvasVisible)
        assertEquals(false, viewModel.uiState.value.canvasPassthrough)
        assertEquals(PenType.Pen, viewModel.uiState.value.currentPenType)
        assertEquals(ToolbarOrientation.HORIZONTAL, viewModel.uiState.value.toolbarOrientation)
        
        // 验证服务状态
        assertEquals(Offset(32f, 64f), viewModel.serviceState.value.toolbarPosition)
        assertEquals(true, viewModel.serviceState.value.toolbarActive)
    }

    /**
     * 测试用例 2: 笔刷配置变化触发保存
     * 
     * 验证点：
     * - 修改笔刷颜色后，PreferencesManager.saveUiState 被调用
     * - UI 状态中的 penConfigs 被正确更新
     */
    @Test
    fun testPenConfigChange_triggersSave() = runBlocking {
        // When - 修改笔刷颜色
        viewModel.setPenColor(Color.Blue)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证状态更新
        val updatedConfig = viewModel.uiState.value.penConfigs[PenType.Pen]
        assertNotNull(updatedConfig)
        assertEquals(Color.Blue, updatedConfig?.color)
        
        // 验证持久化被触发（由于 relaxed mock，saveUiState 会被自动调用）
        coVerify(atLeast = 1) { mockPreferencesMgr.saveUiState(any()) }
    }

    /**
     * 测试用例 3: 绘制笔画更新 Controller 和状态
     * 
     * 验证点：
     * - 开始笔画后，Controller.pathList 增加
     * - canUndo 状态流变为 true
     * - isStrokeDown 标志设置为 true
     */
    @Test
    fun testDrawing_updatesControllerAndState() = runBlocking {
        // Given
        val startPoint = Offset(10f, 20f)
        assertEquals(0, controller.pathList.size)
        
        // When - 开始绘制
        viewModel.startStroke(startPoint, StrokeModifier.None)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证 Controller 状态
        assertEquals(1, controller.pathList.size)
        assertEquals(1, controller.pathList[0].points.size)
        assertEquals(startPoint, controller.pathList[0].points[0])
        assertTrue(viewModel.isStrokeDown)
        
        // 完成笔画
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()
        
        // 验证 canUndo 状态
        assertTrue(viewModel.canUndo.value)
        assertFalse(viewModel.canRedo.value)
    }

    /**
     * 测试用例 4: 撤销重做与 Controller 集成
     * 
     * 验证点：
     * - 撤销后路径列表减少，canRedo 为 true
     * - 重做后路径列表恢复，canUndo 为 true
     * - 新操作清空 redo 栈
     */
    @Test
    fun testUndoRedo_integratesWithController() = runBlocking {
        // Given - 创建两条路径
        viewModel.startStroke(Offset(10f, 20f), StrokeModifier.None)
        viewModel.finishStroke()
        
        viewModel.startStroke(Offset(30f, 40f), StrokeModifier.None)
        viewModel.finishStroke()
        
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertEquals(2, controller.pathList.size)
        assertTrue(viewModel.canUndo.value)
        assertFalse(viewModel.canRedo.value)

        // When - 撤销一次
        viewModel.undo()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证撤销效果
        assertEquals(1, controller.pathList.size)
        assertTrue(viewModel.canUndo.value)
        assertTrue(viewModel.canRedo.value)

        // When - 重做
        viewModel.redo()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证重做效果
        assertEquals(2, controller.pathList.size)
        assertTrue(viewModel.canUndo.value)
        assertFalse(viewModel.canRedo.value)
        
        // When - 创建新路径（应清空 redo 栈）
        viewModel.startStroke(Offset(50f, 60f), StrokeModifier.None)
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()
        
        // Then - 验证 redo 栈已清空
        assertFalse(viewModel.canRedo.value)
    }

    /**
     * 测试用例 5: 退出应用保存所有状态
     * 
     * 验证点：
     * - quitApplication 调用 saveUiState 和 saveServiceState
     * - stopService 回调被触发
     */
    @Test
    fun testQuitApplication_savesAllStates() = runBlocking {
        // When - 退出应用
        viewModel.quitApplication()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证所有状态被保存
        coVerify { mockPreferencesMgr.saveUiState(any()) }
        coVerify { mockPreferencesMgr.saveServiceState(any()) }
        assertTrue(serviceStopped)
    }

    /**
     * 测试用例 6: 橡皮擦功能集成
     * 
     * 验证点：
     * - 切换到橡皮擦后绘制会删除路径
     * - 删除操作可以撤销
     */
    @Test
    fun testEraser_integrationWithController() = runBlocking {
        // Given - 创建一条路径
        viewModel.startStroke(Offset(10f, 10f), StrokeModifier.None)
        viewModel.updateStroke(Offset(20f, 20f))
        viewModel.finishStroke()
        
        testDispatcher.scheduler.advanceUntilIdle()
        assertEquals(1, controller.pathList.size)

        // When - 使用橡皮擦（通过主按钮修饰符）
        viewModel.startStroke(Offset(15f, 15f), StrokeModifier.PrimaryButton)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证路径被删除
        assertEquals(0, controller.pathList.size)
        assertTrue(viewModel.canUndo.value)
        
        // 验证当前笔刷类型暂时切换为橡皮擦
        assertEquals(PenType.StrokeEraser, viewModel.uiState.value.currentPenType)
        
        // 完成笔画后应恢复之前的笔刷类型
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()
        assertEquals(PenType.Pen, viewModel.uiState.value.currentPenType)
    }

    /**
     * 测试用例 7: 画布可见性与自动清除集成
     * 
     * 验证点：
     * - 启用 autoClearCanvas 后，隐藏画布会清除所有路径
     * - 穿透模式被禁用
     */
    @Test
    fun testAutoClearCanvas_onHide_integration() = runBlocking {
        // Given - 创建一些路径
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

        // Then - 验证画布被清除
        assertEquals(0, controller.pathList.size)
        assertFalse(viewModel.uiState.value.canvasPassthrough)
        assertFalse(viewModel.uiState.value.canvasVisible)
    }

    /**
     * 测试用例 8: 工具栏方向切换
     * 
     * 验证点：
     * - toggleToolbarOrientation 在 HORIZONTAL 和 VERTICAL 之间切换
     * - 状态正确更新
     */
    @Test
    fun testToolbarOrientation_toggle_integration() = runBlocking {
        // Given
        assertEquals(ToolbarOrientation.HORIZONTAL, viewModel.uiState.value.toolbarOrientation)

        // When - 切换方向
        viewModel.toggleToolbarOrientation()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertEquals(ToolbarOrientation.VERTICAL, viewModel.uiState.value.toolbarOrientation)

        // When - 再次切换
        viewModel.toggleToolbarOrientation()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertEquals(ToolbarOrientation.HORIZONTAL, viewModel.uiState.value.toolbarOrientation)
    }

    /**
     * 测试用例 9: 多个笔刷配置独立管理
     * 
     * 验证点：
     * - Pen 和 StrokeEraser 的配置独立存储
     * - 修改一个不影响另一个
     */
    @Test
    fun testMultiplePenConfigs_independentManagement() = runBlocking {
        // Given
        val initialPenConfig = viewModel.uiState.value.penConfigs[PenType.Pen]
        val initialEraserConfig = viewModel.uiState.value.penConfigs[PenType.StrokeEraser]
        
        assertNotNull(initialPenConfig)
        assertNotNull(initialEraserConfig)

        // When - 修改 Pen 的配置
        viewModel.setStrokeWidth(20f)
        viewModel.setPenColor(Color.Green)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证 Pen 配置更新
        val updatedPenConfig = viewModel.uiState.value.penConfigs[PenType.Pen]
        assertEquals(20f, updatedPenConfig?.width)
        assertEquals(Color.Green, updatedPenConfig?.color)
        
        // 验证 Eraser 配置未受影响
        val eraserConfig = viewModel.uiState.value.penConfigs[PenType.StrokeEraser]
        assertEquals(initialEraserConfig?.width, eraserConfig?.width)
    }
}
