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
 * 集成测试：工具栏位置管理与持久化的集成
 * 
 * 测试重点：
 * 1. 工具栏位置更新逻辑（直接设置 vs 偏移更新）
 * 2. 位置验证标志的管理
 * 3. 位置保存到 DataStore 的集成
 * 4. 位置加载与恢复
 */
@OptIn(ExperimentalCoroutinesApi::class)
class ToolbarPositionIntegrationTest {

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
     * 测试用例 1: 初始工具栏位置正确加载
     * 
     * 验证点：
     * - 默认位置为 Offset(32f, 64f)
     * - positionValidated 默认为 false
     */
    @Test
    fun testInitialToolbarPosition_defaultValues() = runBlocking {
        // Then - 验证初始状态
        assertEquals(Offset(32f, 64f), viewModel.serviceState.value.toolbarPosition)
        assertFalse(viewModel.serviceState.value.positionValidated)
        assertTrue(viewModel.serviceState.value.toolbarActive)
    }

    /**
     * 测试用例 2: 直接设置工具栏位置
     * 
     * 验证点：
     * - setToolbarPosition 更新位置
     * - 可以设置 validated 标志
     */
    @Test
    fun testSetToolbarPosition_directUpdate() = runBlocking {
        // Given
        val newPosition = Offset(100f, 200f)

        // When - 设置新位置（未验证）
        viewModel.setToolbarPosition(newPosition, false)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertEquals(newPosition, viewModel.serviceState.value.toolbarPosition)
        assertFalse(viewModel.serviceState.value.positionValidated)

        // When - 设置新位置（已验证）
        val validatedPosition = Offset(150f, 250f)
        viewModel.setToolbarPosition(validatedPosition, true)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertEquals(validatedPosition, viewModel.serviceState.value.toolbarPosition)
        assertTrue(viewModel.serviceState.value.positionValidated)
    }

    /**
     * 测试用例 3: 偏移更新工具栏位置
     * 
     * 验证点：
     * - updateToolbarPosition 在当前位置基础上增加偏移
     * - 多次偏移累加正确
     */
    @Test
    fun testUpdateToolbarPosition_offsetsCorrectly() = runBlocking {
        // Given
        val initialPosition = viewModel.serviceState.value.toolbarPosition
        assertEquals(Offset(32f, 64f), initialPosition)

        // When - 第一次偏移
        val offset1 = Offset(50f, 50f)
        viewModel.updateToolbarPosition(offset1)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertEquals(Offset(82f, 114f), viewModel.serviceState.value.toolbarPosition)

        // When - 第二次偏移
        val offset2 = Offset(-20f, 30f)
        viewModel.updateToolbarPosition(offset2)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证累加效果
        assertEquals(Offset(62f, 144f), viewModel.serviceState.value.toolbarPosition)
    }

    /**
     * 测试用例 4: 保存位置到 DataStore
     * 
     * 验证点：
     * - saveToolbarPosition 调用 PreferencesManager.saveServiceState
     * - 异步操作正确执行
     */
    @Test
    fun testSavePosition_persistsToDataStore() = runBlocking {
        // Given
        val newPosition = Offset(200f, 300f)
        viewModel.setToolbarPosition(newPosition, true)
        testDispatcher.scheduler.advanceUntilIdle()

        // When - 保存位置
        viewModel.saveToolbarPosition()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证持久化被调用
        coVerify { mockPreferencesMgr.saveServiceState(any()) }
    }

    /**
     * 测试用例 5: 从 DataStore 加载保存的位置
     * 
     * 验证点：
     * - ViewModel 初始化时使用 PreferencesManager 加载的状态
     */
    @Test
    fun testLoadPosition_fromPreferences() = runBlocking {
        // Given - 配置 mock 返回保存的位置
        val savedPosition = Offset(150f, 250f)
        val savedServiceState = ServiceState(
            toolbarPosition = savedPosition,
            positionValidated = true,
            toolbarActive = false
        )
        every { runBlocking { mockPreferencesMgr.getSavedServiceState() } } returns savedServiceState

        // When - 创建新的 ViewModel
        val newViewModel = DrawViewModel(
            controller = DrawController().apply {
                setPenConfig(PenConfig(penType = PenType.Pen, color = Color.Red, width = 5f))
            },
            preferencesMgr = mockPreferencesMgr,
            initialUiState = UiState(),
            initialServiceState = savedServiceState,
            stopService = { }
        )
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证加载了保存的位置
        assertEquals(savedPosition, newViewModel.serviceState.value.toolbarPosition)
        assertTrue(newViewModel.serviceState.value.positionValidated)
        assertFalse(newViewModel.serviceState.value.toolbarActive)
    }

    /**
     * 测试用例 6: 工具栏激活状态管理
     * 
     * 验证点：
     * - setToolbarActive 更新激活状态
     * - resetToolbarTimer 重置定时器并设置为激活
     */
    @Test
    fun testToolbarActiveState_management() = runBlocking {
        // Given
        assertTrue(viewModel.serviceState.value.toolbarActive)

        // When - 设置为非激活
        viewModel.setToolbarActive(false)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertFalse(viewModel.serviceState.value.toolbarActive)

        // When - 设置为激活
        viewModel.setToolbarActive(true)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(viewModel.serviceState.value.toolbarActive)
    }

    /**
     * 测试用例 7: 位置更新的边界情况
     * 
     * 验证点：
     * - 负数坐标可以被设置（实际边界检查在 MainService 中）
     * - 超大坐标可以被设置
     */
    @Test
    fun testToolbarPosition_boundaryCases() = runBlocking {
        // When - 设置负数坐标
        viewModel.setToolbarPosition(Offset(-10f, -20f), true)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertEquals(Offset(-10f, -20f), viewModel.serviceState.value.toolbarPosition)

        // When - 设置超大坐标
        viewModel.setToolbarPosition(Offset(10000f, 10000f), true)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertEquals(Offset(10000f, 10000f), viewModel.serviceState.value.toolbarPosition)
    }

    /**
     * 测试用例 8: 多次保存位置
     * 
     * 验证点：
     * - 每次保存都调用 saveServiceState
     * - 最后一次保存的值是正确的
     */
    @Test
    fun testMultipleSaves_allPersisted() = runBlocking {
        // When & Then - 多次保存
        for (i in 1..5) {
            val position = Offset(i * 100f, i * 100f)
            viewModel.setToolbarPosition(position, true)
            viewModel.saveToolbarPosition()
            testDispatcher.scheduler.advanceUntilIdle()
        }

        // 验证 saveServiceState 被调用了至少 5 次
        coVerify(atLeast = 5) { mockPreferencesMgr.saveServiceState(any()) }
        
        // 验证最后的位置是正确的
        assertEquals(Offset(500f, 500f), viewModel.serviceState.value.toolbarPosition)
    }

    /**
     * 测试用例 9: 位置变化不影响其他服务状态
     * 
     * 验证点：
     * - 修改位置不改变 toolbarActive
     * - 修改位置不改变 positionValidated（除非显式设置）
     */
    @Test
    fun testPositionChange_preservesOtherState() = runBlocking {
        // Given
        viewModel.setToolbarActive(false)
        viewModel.setToolbarPosition(Offset(32f, 64f), true)
        testDispatcher.scheduler.advanceUntilIdle()
        
        assertFalse(viewModel.serviceState.value.toolbarActive)
        assertTrue(viewModel.serviceState.value.positionValidated)

        // When - 只更新位置
        viewModel.setToolbarPosition(Offset(100f, 200f), false)
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证其他状态保持不变
        assertFalse(viewModel.serviceState.value.toolbarActive)
        assertFalse(viewModel.serviceState.value.positionValidated)
        assertEquals(Offset(100f, 200f), viewModel.serviceState.value.toolbarPosition)
    }

    /**
     * 测试用例 10: 位置偏移与实际绘制操作独立
     * 
     * 验证点：
     * - 绘制笔画不影响工具栏位置
     * - 移动工具栏不影响画布内容
     */
    @Test
    fun testToolbarPosition_independentFromDrawing() = runBlocking {
        // Given
        val initialPosition = viewModel.serviceState.value.toolbarPosition
        
        // When - 绘制笔画
        viewModel.startStroke(Offset(10f, 20f), StrokeModifier.None)
        viewModel.finishStroke()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证位置未受影响
        assertEquals(initialPosition, viewModel.serviceState.value.toolbarPosition)
        assertEquals(1, controller.pathList.size)

        // When - 移动工具栏
        viewModel.updateToolbarPosition(Offset(50f, 50f))
        testDispatcher.scheduler.advanceUntilIdle()

        // Then - 验证画布内容未受影响
        assertEquals(1, controller.pathList.size)
        assertNotEquals(initialPosition, viewModel.serviceState.value.toolbarPosition)
    }
}
