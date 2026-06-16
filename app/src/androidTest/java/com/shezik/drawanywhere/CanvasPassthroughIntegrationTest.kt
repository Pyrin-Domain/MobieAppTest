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
 * 集成测试：画布穿透模式与状态管理的集成
 * 
 * 测试重点：
 * 1. 穿透模式切换时 UI 状态的更新
 * 2. 自动清除画布时穿透模式的联动
 * 3. 画布可见性变化对抽屉状态的影响
 * 
 * 注意：由于无法在单元测试中访问真实的 WindowManager.LayoutParams，
 * 我们主要测试 ViewModel 层面的状态变化逻辑。
 * 真实的 LayoutParams.flags 更新需要在设备上进行手动测试或使用 UiAutomator。
 */
@OptIn(ExperimentalCoroutinesApi::class)
class CanvasPassthroughIntegrationTest {

    private lateinit var viewModel: DrawViewModel
    private lateinit var controller: DrawController
    private lateinit var mockPreferencesMgr: PreferencesManager

    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        
        controller = DrawController()
        controller.setPenConfig(PenConfig(penType = PenType.Pen, color = Color.Red, width = 5f, alpha = 1f))
        
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
     * 测试用例 1: 切换穿透模式更新状态
     * 
     * 验证点：
     * - toggleCanvasPassthrough 翻转 canvasPassthrough 状态
     * - secondDrawerPinnedButtons 包含 "passthrough"
     */
    @Test
    fun testTogglePassthrough_updatesState() = runBlocking {
        // Given
        assertFalse(viewModel.uiState.value.canvasPassthrough)
        assertFalse(viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))

        // When - 启用穿透模式
        viewModel.toggleCanvasPassthrough()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.uiState.value.canvasPassthrough)
        assertTrue(viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))

        // When - 再次切换（禁用）
        viewModel.toggleCanvasPassthrough()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertFalse(viewModel.uiState.value.canvasPassthrough)
        assertFalse(viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))
    }

    /**
     * 测试用例 2: 直接设置穿透模式
     * 
     * 验证点：
     * - setCanvasPassthrough(true) 启用穿透
     * - setCanvasPassthrough(false) 禁用穿透
     */
    @Test
    fun testSetCanvasPassthrough_directControl() = runBlocking {
        // When - 直接启用
        viewModel.setCanvasPassthrough(true)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.uiState.value.canvasPassthrough)
        assertTrue(viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))

        // When - 直接禁用
        viewModel.setCanvasPassthrough(false)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertFalse(viewModel.uiState.value.canvasPassthrough)
        assertFalse(viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))
    }

    /**
     * 测试用例 3: 隐藏画布时自动清除并禁用穿透
     * 
     * 验证点：
     * - autoClearCanvas = true 时，隐藏画布会清除路径
     * - canvasPassthrough 被设置为 false
     * - "passthrough" 从 pinned buttons 中移除
     */
    @Test
    fun testAutoClear_onHide_withPassthrough() = runBlocking {
        // Given - 创建一些路径
        viewModel.startStroke(Offset(10f, 20f), StrokeModifier.None)
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertEquals(1, controller.pathList.size)
        
        // 启用穿透模式
        viewModel.setCanvasPassthrough(true)
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertTrue(viewModel.uiState.value.canvasPassthrough)
        assertTrue(viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))
        
        // 启用自动清除
        viewModel.setAutoClearCanvas(true)
        testDispatcher.scheduler.advanceUntilIdle()

        // When - 隐藏画布
        viewModel.setCanvasVisibility(false)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证所有联动效果
        assertFalse(viewModel.uiState.value.canvasVisible)
        assertFalse(viewModel.uiState.value.canvasPassthrough)
        assertFalse(viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))
        assertEquals(0, controller.pathList.size)
    }

    /**
     * 测试用例 4: 画布可见性变化影响抽屉状态
     * 
     * 验证点：
     * - 切换可见性时 firstDrawerOpen 状态翻转
     */
    @Test
    fun testVisibility_affectsDrawerState() = runBlocking {
        // Given
        assertTrue(viewModel.uiState.value.firstDrawerOpen)  // 默认与 canvasVisible 相同

        // When - 隐藏画布
        viewModel.toggleCanvasVisibility()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证抽屉状态翻转
        assertFalse(viewModel.uiState.value.canvasVisible)
        assertFalse(viewModel.uiState.value.firstDrawerOpen)

        // When - 显示画布
        viewModel.toggleCanvasVisibility()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.uiState.value.canvasVisible)
        assertTrue(viewModel.uiState.value.firstDrawerOpen)
    }

    /**
     * 测试用例 5: 穿透模式固定按钮的独立控制
     * 
     * 验证点：
     * - pinSecondDrawerButton 可以独立控制按钮固定状态
     * - toggleSecondDrawerPinned 翻转固定状态
     */
    @Test
    fun testPassthroughPin_independentControl() = runBlocking {
        // Given
        assertFalse(viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))

        // When - 固定 passthrough 按钮
        viewModel.pinSecondDrawerButton("passthrough", true)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))

        // When - 取消固定
        viewModel.toggleSecondDrawerPinned("passthrough")
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertFalse(viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))
    }

    /**
     * 测试用例 6: 多次切换穿透模式的状态一致性
     * 
     * 验证点：
     * - 多次切换后状态仍然正确
     * - pinned buttons 集合正确维护
     */
    @Test
    fun testMultipleToggles_stateConsistency() = runBlocking {
        // When & Then - 多次切换
        for (i in 1..5) {
            viewModel.toggleCanvasPassthrough()
            testDispatcher.scheduler.advanceUntilIdle()
            
            val expectedPassthrough = i % 2 == 1
            assertEquals(expectedPassthrough, viewModel.uiState.value.canvasPassthrough)
            assertEquals(expectedPassthrough, viewModel.uiState.value.secondDrawerPinnedButtons.contains("passthrough"))
        }
    }

    /**
     * 测试用例 7: 穿透模式与其他操作互不影响
     * 
     * 验证点：
     * - 穿透模式开启时仍可正常绘制
     * - 绘制操作不影响穿透状态
     */
    @Test
    fun testPassthrough_doesNotAffectDrawing() = runBlocking {
        // Given - 启用穿透模式
        viewModel.setCanvasPassthrough(true)
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertTrue(viewModel.uiState.value.canvasPassthrough)

        // When - 绘制笔画
        viewModel.startStroke(Offset(10f, 20f), StrokeModifier.None)
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证穿透模式未受影响
        assertTrue(viewModel.uiState.value.canvasPassthrough)
        assertEquals(1, controller.pathList.size)
    }

    /**
     * 测试用例 8: 清除画布不影响穿透模式
     * 
     * 验证点：
     * - clearCanvas 不清除穿透状态
     */
    @Test
    fun testClearCanvas_preservesPassthrough() = runBlocking {
        // Given
        viewModel.setCanvasPassthrough(true)
        viewModel.startStroke(Offset(10f, 20f), StrokeModifier.None)
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertTrue(viewModel.uiState.value.canvasPassthrough)
        assertEquals(1, controller.pathList.size)

        // When - 清除画布
        viewModel.clearCanvas()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证穿透模式保持
        assertTrue(viewModel.uiState.value.canvasPassthrough)
        assertEquals(0, controller.pathList.size)
    }

    /**
     * 测试用例 9: 撤销重做不影响穿透模式
     * 
     * 验证点：
     * - undo/redo 操作不改变 canvasPassthrough 状态
     */
    @Test
    fun testUndoRedo_preservesPassthrough() = runBlocking {
        // Given
        viewModel.setCanvasPassthrough(true)
        viewModel.startStroke(Offset(10f, 20f), StrokeModifier.None)
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertTrue(viewModel.uiState.value.canvasPassthrough)

        // When - 撤销
        viewModel.undo()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.uiState.value.canvasPassthrough)
        assertEquals(0, controller.pathList.size)

        // When - 重做
        viewModel.redo()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.uiState.value.canvasPassthrough)
        assertEquals(1, controller.pathList.size)
    }
}
